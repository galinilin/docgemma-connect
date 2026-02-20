"""Agent node implementations for DocGemma v3.

6-node architecture with binary intent classification and reactive tool loop.
Every design decision is grounded in 856 experiments on MedGemma 4B.

Nodes:
  1. input_assembly     — deterministic entity extraction (no LLM)
  2. intent_classify    — LLM + Outlines, T=0.0
  3. tool_select        — LLM + Outlines, two-stage, T=0.0
  4. tool_execute       — deterministic tool dispatch (async)
  5. result_classify    — LLM + Outlines, T=0.0
  6. synthesize         — LLM free-form streaming, T=0.5
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Callable

from .prompts import (
    ACTION_VERBS,
    COMMON_DRUGS,
    DIRECT_CHAT_PROMPT,
    ERROR_TEMPLATES,
    INTENT_CLASSIFY_PROMPT,
    MAX_STEPS,
    MAX_TOKENS,
    PRELIMINARY_THINKING_PROMPT,
    RESULT_CLASSIFY_PROMPT,
    SYNTHESIZE_SYSTEM_PROMPT,
    SYNTHESIZE_USER_TEMPLATE,
    TASK_PATTERNS,
    TEMPERATURE,
    TOOL_ARG_THINKING_PROMPT,
    TOOL_CLINICAL_LABELS,
    TOOL_DESCRIPTIONS,
    TOOL_EXAMPLES,
    TOOL_SELECT_STAGE1_PROMPT,
    TOOL_SELECT_STAGE2_PROMPT,
    WRITE_TOOLS,
)
from .schemas import (
    IntentClassification,
    ResultAssessment,
    ToolSelection,
    TOOL_ARG_SCHEMAS,
)
from .state import AgentState, ExtractedEntities, ToolResult

if TYPE_CHECKING:
    from ..model import DocGemma

logger = logging.getLogger(__name__)

# Callback type for streaming tokens during generation
StreamCallback = Callable[[str], Awaitable[None]] | None


# =============================================================================
# Constants
# =============================================================================

# Regex: UUID patient IDs (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
_UUID_RE = re.compile(
    r"\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b", re.IGNORECASE
)

# Regex: Short patient IDs (abc-123)
_SHORT_ID_RE = re.compile(r"\b[a-z]{3}-\d{3}\b")

# Per-tool description snippets for TOOL_SELECT Stage 2 prompts
_TOOL_STAGE2_DESC: dict[str, str] = {
    "check_drug_safety": (
        "Look up FDA boxed warnings and safety alerts for a drug. "
        "Args: drug_name (str)"
    ),
    "check_drug_interactions": (
        "Check interactions between 2+ drugs. "
        "Args: drug_names (list[str], min 2)"
    ),
    "search_medical_literature": (
        "Search PubMed for studies. Args: query (str)"
    ),
    "find_clinical_trials": (
        "Search ClinicalTrials.gov. "
        "Args: condition (str), status (str, optional)"
    ),
    "search_patient": (
        "Search EHR for a patient by name. Args: name (str)"
    ),
    "get_patient_chart": (
        "Get full clinical summary. Args: patient_id (str)"
    ),
    "prescribe_medication": (
        "Create medication order. "
        "Args: patient_id (str), medication_name (str), dosage (str), frequency (str)"
    ),
    "add_allergy": (
        "Document allergy. "
        "Args: patient_id (str), substance (str), reaction (str), severity (str, optional)"
    ),
    "save_clinical_note": (
        "Save clinical note. "
        "Args: patient_id (str), note_type (str), note_text (str)"
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for logging."""
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _extract_patient_ids(text: str) -> list[str]:
    """Extract patient IDs from text using regex patterns."""
    ids: list[str] = []
    ids.extend(_UUID_RE.findall(text))
    ids.extend(_SHORT_ID_RE.findall(text))
    return ids


def _extract_drug_mentions(text: str) -> list[str]:
    """Extract drug names by word-boundary dictionary matching."""
    text_lower = text.lower()
    found = []
    for drug in COMMON_DRUGS:
        pattern = r"\b" + re.escape(drug) + r"\b"
        if re.search(pattern, text_lower):
            found.append(drug)
    return found


def _extract_action_verbs(text: str) -> list[str]:
    """Extract action verbs from text."""
    text_lower = text.lower()
    found = []
    for verb in ACTION_VERBS:
        if " " in verb:
            # Multi-word phrases: substring match
            if verb in text_lower:
                found.append(verb)
        else:
            pattern = r"\b" + re.escape(verb) + r"\b"
            if re.search(pattern, text_lower):
                found.append(verb)
    return found


def _collect_args_for_registry(
    tool_name: str, schema_args: dict[str, Any], state: dict
) -> dict[str, Any]:
    """Map per-tool schema fields to registry executor parameter names.

    Most fields pass through directly. Special cases:
    - check_drug_interactions: drug_names (list) → drugs (list)
    """
    args = {k: v for k, v in schema_args.items() if v is not None}

    # Schema has drug_names (list), executor expects drugs (list)
    if tool_name == "check_drug_interactions" and "drug_names" in args:
        args["drugs"] = args.pop("drug_names")

    return args


def _format_tool_result(result: ToolResult) -> str:
    """Format a single tool result with clinical label for synthesis."""
    label = result.get("tool_label", result.get("tool_name", "Unknown"))
    if result.get("success"):
        data = result.get("result", {})
        data_str = json.dumps(data, default=str)
        if len(data_str) > 1000:
            data_str = data_str[:1000] + "..."
        return f"{label}:\n{data_str}"
    error = result.get("error", "Unknown error")
    return f"{label}: {error}"


def _patient_context_section(state: dict) -> str:
    """Build patient context section for prompt injection.

    Returns empty string if no patient is selected, so the prompt
    template collapses cleanly.
    """
    ctx = state.get("patient_context")
    if not ctx:
        return ""
    pid = state.get("session_patient_id", "")
    header = f"\nActive patient record (ID: {pid}):\n" if pid else "\nActive patient record:\n"
    return f"{header}{ctx}\n"


def _thinking_context_section(state: dict) -> str:
    """Build thinking context section for prompt injection.

    Returns empty string if no preliminary thinking was produced, so
    the prompt template collapses cleanly.
    """
    text = state.get("preliminary_thinking_text")
    if not text:
        return ""
    return f"\nPreliminary reasoning:\n{text}\n"


def _format_error_for_synthesis(error_messages: list[str]) -> str:
    """Format error messages for synthesis prompt (pre-formatted, clinician-safe)."""
    if not error_messages:
        return ""
    return "\n".join(f"- {msg}" for msg in error_messages)


def _classify_error(error_str: str) -> str:
    """Classify an error string into a category for ERROR_TEMPLATES."""
    error_lower = error_str.lower()
    if any(kw in error_lower for kw in ("timeout", "timed out")):
        return "timeout"
    if any(kw in error_lower for kw in ("not found", "no results", "no match")):
        return "not_found"
    if any(kw in error_lower for kw in ("argument", "missing", "required", "invalid")):
        return "invalid_args"
    if any(kw in error_lower for kw in ("rate limit", "too many requests")):
        return "rate_limit"
    if any(kw in error_lower for kw in ("server error", "500", "internal")):
        return "server_error"
    if "multiple" in error_lower:
        return "multiple_matches"
    return "generic"


def _is_duplicate_tool_call(
    tool_name: str, args: dict, tool_results: list[ToolResult]
) -> bool:
    """Detect if this exact tool call was already executed (stuck loop prevention)."""
    for prev in tool_results:
        if prev.get("tool_name") == tool_name and prev.get("args") == args:
            return True
    return False


def _match_task_pattern(query: str, pattern: dict) -> bool:
    """Check if a query matches a task pattern's keyword rules."""
    query_lower = query.lower()

    # "keywords" — any keyword matches
    if "keywords" in pattern:
        if any(kw in query_lower for kw in pattern["keywords"]):
            return True

    # "keywords_all" — every group must match (pipe-separated alternatives)
    if "keywords_all" in pattern:
        for group in pattern["keywords_all"]:
            alternatives = group.split("|")
            if not any(alt in query_lower for alt in alternatives):
                return False
        return True

    return False


def _task_pattern_satisfied(
    query: str, tool_results: list[ToolResult]
) -> bool:
    """Check if all required tools for the matched task pattern have been executed.

    Deterministic termination logic (V3 spec Section 11).
    """
    completed_tools = {r["tool_name"] for r in tool_results if r.get("success")}

    for pattern in TASK_PATTERNS.values():
        if _match_task_pattern(query, pattern):
            required = pattern["requires"]
            if required.issubset(completed_tools):
                return True

    return False


def _needs_user_clarification(tool_results: list[ToolResult]) -> str | None:
    """Check if the latest result requires user clarification.

    Returns clarification message or None.
    """
    if not tool_results:
        return None

    last = tool_results[-1]
    if not last.get("success"):
        return None

    result = last.get("result", {})

    # Multiple patient matches → ask user to clarify
    if last.get("tool_name") == "search_patient":
        patients = result.get("patients", [])
        if len(patients) > 1:
            names = [p.get("name", "Unknown") for p in patients[:5]]
            return (
                f"Multiple patients found: {', '.join(names)}. "
                "Please specify which patient you mean."
            )

    return None


# =============================================================================
# Preliminary Thinking (optional pre-reasoning step, gated by thinking_enabled)
# =============================================================================


async def preliminary_thinking(
    state: AgentState,
    model: DocGemma,
    stream_callback: StreamCallback = None,
) -> dict:
    """Generate preliminary reasoning about the query.

    Async streaming LLM generation at T=0.5 with thinking tokens preserved.
    Streams tokens to the frontend via stream_callback, then stores the
    full text in state for downstream prompt injection.
    """
    query = state.get("user_query", "")
    context = _patient_context_section(state)
    history = state.get("conversation_history", [])

    image_findings = state.get("image_findings")
    image_section = f"\nImage findings:\n{image_findings}\n" if image_findings else ""

    tool_calling_enabled = state.get("tool_calling_enabled", True)
    tools_section = f"\nAvailable tools:\n{TOOL_DESCRIPTIONS}\n" if tool_calling_enabled else ""

    prompt = PRELIMINARY_THINKING_PROMPT.format(
        user_query=query,
        patient_context_section=context,
        image_section=image_section,
        tools_section=tools_section,
    )

    chunks: list[str] = []
    async for chunk in model.generate_stream(
        prompt,
        max_new_tokens=MAX_TOKENS["preliminary_thinking"],
        do_sample=True,
        temperature=TEMPERATURE["preliminary_thinking"],
        messages=history,
        filter_thinking=False,
    ):
        if stream_callback:
            await stream_callback(chunk)
        chunks.append(chunk)

    response = "".join(chunks)

    logger.info(
        f"[PRELIMINARY_THINKING] Generated {len(response)} chars of reasoning"
    )

    return {"preliminary_thinking_text": response}


def route_after_input_assembly(state: dict) -> str:
    """Route after input assembly: thinking node if enabled, else intent classify."""
    if state.get("thinking_enabled"):
        logger.info("[ROUTE] input_assembly → preliminary_thinking (thinking enabled)")
        return "preliminary_thinking"
    logger.info("[ROUTE] input_assembly → intent_classify")
    return "intent_classify"


# =============================================================================
# Node 1: INPUT_ASSEMBLY (deterministic, no LLM)
# =============================================================================


async def input_assembly(state: AgentState) -> dict:
    """Assemble input with deterministic entity extraction.

    Extracts patient IDs, drug mentions, and action verbs from the query.
    When a session patient is selected, pre-fetches the patient chart summary
    so all downstream nodes (including DIRECT route) have clinical context.
    """
    query = state.get("user_query", "")

    patient_ids = _extract_patient_ids(query)

    # Inject session patient ID from frontend selector
    session_pid = state.get("session_patient_id")
    if session_pid and session_pid not in patient_ids:
        patient_ids.append(session_pid)

    entities: ExtractedEntities = {
        "patient_ids": patient_ids,
        "drug_mentions": _extract_drug_mentions(query),
        "action_verbs": _extract_action_verbs(query),
        "has_image": state.get("image_data") is not None,
    }

    logger.info(
        f"[INPUT_ASSEMBLY] entities: "
        f"patient_ids={entities['patient_ids']}, "
        f"drugs={entities['drug_mentions']}, "
        f"verbs={entities['action_verbs']}, "
        f"image={entities['has_image']}"
    )

    result: dict[str, Any] = {"extracted_entities": entities}

    # Pre-process image: run analysis before routing so findings are
    # available to all downstream nodes (including DIRECT route).
    if entities["has_image"]:
        try:
            from ..tools.image_analysis import analyze_medical_image
            from ..tools.schemas import ImageAnalysisInput

            img_result = await analyze_medical_image(
                ImageAnalysisInput(image_data=state["image_data"], query=query)
            )
            if img_result.findings and not img_result.error:
                result["image_findings"] = img_result.findings
                logger.info("[INPUT_ASSEMBLY] Image analysis completed")
            else:
                logger.warning(f"[INPUT_ASSEMBLY] Image analysis failed: {img_result.error}")
        except Exception as e:
            logger.warning(f"[INPUT_ASSEMBLY] Image analysis error: {e}")

    # Pre-fetch patient chart when a session patient is selected
    if session_pid:
        try:
            from ..tools.fhir_store import get_patient_chart
            from ..tools.fhir_store.schemas import GetPatientChartInput

            chart = await get_patient_chart(GetPatientChartInput(patient_id=session_pid))
            if chart.result and not chart.error:
                result["patient_context"] = chart.result
                logger.info(f"[INPUT_ASSEMBLY] Pre-fetched chart for patient {session_pid}")
            else:
                logger.warning(f"[INPUT_ASSEMBLY] Chart fetch failed for {session_pid}: {chart.error}")
        except Exception as e:
            logger.warning(f"[INPUT_ASSEMBLY] Chart fetch error for {session_pid}: {e}")

    return result


# =============================================================================
# Node 2: INTENT_CLASSIFY (LLM + Outlines, T=0.0)
# =============================================================================


def intent_classify(state: AgentState, model: DocGemma) -> dict:
    """Classify query as DIRECT or TOOL_NEEDED.

    Single constrained generation call at T=0.0 (deterministic).
    Image findings (if any) are injected into the context so the model
    routes based on the actual query, not the presence of an image.
    """
    # Tools disabled from frontend → force DIRECT route
    if not state.get("tool_calling_enabled", True):
        logger.info("[INTENT_CLASSIFY] Tools disabled by user, forcing DIRECT")
        return {
            "intent": "DIRECT",
            "task_summary": "Direct response (tools disabled)",
            "suggested_tool": None,
        }

    context = _patient_context_section(state)
    if state.get("image_findings"):
        context += f"\nAttached image findings:\n{state['image_findings']}\n"

    prompt = INTENT_CLASSIFY_PROMPT.format(
        user_query=state.get("user_query", ""),
        thinking_section=_thinking_context_section(state),
        patient_context_section=context,
    )
    history = state.get("conversation_history", [])

    result = model.generate_outlines(
        prompt,
        IntentClassification,
        temperature=TEMPERATURE["intent_classify"],
        max_new_tokens=MAX_TOKENS["intent_classify"],
        messages=history,
    )

    logger.info(
        f"[INTENT_CLASSIFY] intent={result.intent}, "
        f"suggested_tool={result.suggested_tool}, "
        f"summary={_truncate(result.task_summary)}"
    )

    return {
        "intent": result.intent,
        "task_summary": result.task_summary,
        "suggested_tool": result.suggested_tool,
    }


# =============================================================================
# Node 3: TOOL_SELECT (LLM + Outlines, two-stage, T=0.0)
# =============================================================================


def tool_select(state: AgentState, model: DocGemma) -> dict:
    """Select tool and extract arguments in two stages.

    Stage 1: Select tool name (single field, no nullable distractors).
    Stage 2: Extract per-tool arguments with entity hints.
    1-shot matched example for Stage 1 (91% arg accuracy, Part II Section 19).
    """
    query = state.get("user_query", "")
    task_summary = state.get("task_summary", "")
    suggested = state.get("suggested_tool")
    entities = state.get("extracted_entities", {})
    history = state.get("conversation_history", [])

    # ── Stage 1: Tool Selection ──
    example = TOOL_EXAMPLES.get(suggested, TOOL_EXAMPLES["check_drug_safety"])

    stage1_prompt = TOOL_SELECT_STAGE1_PROMPT.format(
        tool_descriptions=TOOL_DESCRIPTIONS,
        example_query=example[0],
        example_tool=example[1],
        task_summary=task_summary,
        user_query=query,
        thinking_section=_thinking_context_section(state),
    )

    tool_result = model.generate_outlines(
        stage1_prompt,
        ToolSelection,
        temperature=TEMPERATURE["tool_select_stage1"],
        max_new_tokens=MAX_TOKENS["tool_select_stage1"],
        messages=history,
    )
    tool_name = tool_result.tool_name
    logger.info(f"[TOOL_SELECT] Stage 1: selected {tool_name}")

    # ── "none" escape hatch: no applicable tool ──
    if tool_name == "none":
        logger.info("[TOOL_SELECT] No applicable tool — routing to synthesize")
        return {
            "current_tool": "none",
            "current_args": {},
            "_planned_tool": None,
            "_planned_args": None,
        }

    # ── Stage 2: Per-tool Arguments ──
    tool_desc = _TOOL_STAGE2_DESC.get(tool_name, "")
    arg_schema = TOOL_ARG_SCHEMAS.get(tool_name)

    if not arg_schema:
        logger.warning(f"[TOOL_SELECT] No arg schema for {tool_name}")
        return {
            "current_tool": tool_name,
            "current_args": {},
            "_planned_tool": tool_name,
            "_planned_args": {},
        }

    # Build entity hints from extracted_entities
    hints = []
    if entities.get("patient_ids"):
        hints.append(f"Known patient IDs: {', '.join(entities['patient_ids'])}")
    if entities.get("drug_mentions"):
        hints.append(f"Detected drugs: {', '.join(entities['drug_mentions'])}")
    entity_hints = "\n".join(hints) if hints else ""

    # ── Stage 1.5: Arg Thinking (always runs before argument extraction) ──
    arg_thinking_section = ""
    arg_thinking_prompt = TOOL_ARG_THINKING_PROMPT.format(
        tool_name=tool_name,
        tool_description=tool_desc,
        user_query=query,
        task_summary=task_summary,
        thinking_section=_thinking_context_section(state),
        patient_context_section=_patient_context_section(state),
        entity_hints=f"\nExtracted entities:\n{entity_hints}\n" if entity_hints else "",
    )
    arg_thinking_text = model.generate(
        arg_thinking_prompt,
        max_new_tokens=MAX_TOKENS["tool_arg_thinking"],
        do_sample=True,
        temperature=TEMPERATURE["tool_arg_thinking"],
        messages=history,
    )
    if arg_thinking_text:
        logger.info(
            f"[TOOL_SELECT] Arg thinking: {_truncate(arg_thinking_text)}"
        )
        arg_thinking_section = f"\nArgument reasoning:\n{arg_thinking_text}\n"

    stage2_prompt = TOOL_SELECT_STAGE2_PROMPT.format(
        tool_name=tool_name,
        tool_description=tool_desc,
        user_query=query,
        thinking_section=_thinking_context_section(state),
        arg_thinking_section=arg_thinking_section,
        entity_hints=entity_hints,
    )

    arg_result = model.generate_outlines(
        stage2_prompt,
        arg_schema,
        temperature=TEMPERATURE["tool_select_stage2"],
        max_new_tokens=MAX_TOKENS["tool_select_stage2"],
        messages=history,
    )

    args = arg_result.model_dump()
    logger.info(
        f"[TOOL_SELECT] Stage 2: args={_truncate(json.dumps(args, default=str))}"
    )

    return {
        "current_tool": tool_name,
        "current_args": args,
        "_planned_tool": tool_name,
        "_planned_args": args,
    }


# =============================================================================
# Node 4: TOOL_EXECUTE (deterministic, no LLM — async)
# =============================================================================


async def tool_execute(state: AgentState, tool_executor: Callable) -> dict:
    """Execute the planned tool call.

    Validates args, maps schema fields to registry params, executes,
    and formats results with clinical labels (no tool name leakage).
    Pre-formats errors using ERROR_TEMPLATES (4.8→10/10 quality).
    """
    tool_name = state.get("_planned_tool")
    tool_args = state.get("_planned_args", {})
    step_count = state.get("step_count", 0)

    if not tool_name:
        logger.warning("[TOOL_EXECUTE] No tool planned, skipping")
        return {
            "_planned_tool": None,
            "_planned_args": None,
        }

    # Map per-tool schema args to registry executor params
    registry_args = _collect_args_for_registry(tool_name, tool_args, state)
    tool_label = TOOL_CLINICAL_LABELS.get(tool_name, tool_name)

    logger.info(
        f"[TOOL_EXECUTE] {tool_name} with args: "
        f"{_truncate(json.dumps(registry_args, default=str))}"
    )

    start = time.perf_counter()
    try:
        result = await tool_executor(tool_name, registry_args)
        elapsed_ms = (time.perf_counter() - start) * 1000

        success = not result.get("error")

        # Pre-format error if present
        error_str = None
        error_type = None
        if not success:
            raw_error = str(result.get("error", ""))
            error_type = _classify_error(raw_error)
            error_str = ERROR_TEMPLATES.get(
                error_type, ERROR_TEMPLATES["generic"]
            ).format(
                tool_label=tool_label,
                entity=(
                    tool_args.get("drug_name")
                    or tool_args.get("name")
                    or tool_args.get("query")
                    or ""
                ),
            )

        # Format result for synthesis — truncate string *values* inside
        # the dict so the JSON structure stays valid.
        formatted = ""
        if success:
            truncated = {
                k: (v[:800] + "..." if isinstance(v, str) and len(v) > 800 else v)
                for k, v in result.items()
                if v is not None
            }
            formatted = json.dumps(truncated, default=str)

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "tool_label": tool_label,
            "args": tool_args,
            "result": result,
            "formatted_result": formatted,
            "error": error_str,
            "error_type": error_type,
            "success": success,
        }

        status = "SUCCESS" if success else "ERROR"
        logger.info(f"[TOOL_EXECUTE] {tool_name} {status} in {elapsed_ms:.1f}ms")

        return {
            "tool_results": [tool_result],
            "step_count": step_count + 1,
            "_planned_tool": None,
            "_planned_args": None,
        }

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error(
            f"[TOOL_EXECUTE] {tool_name} EXCEPTION in {elapsed_ms:.1f}ms: {e}"
        )

        error_type = _classify_error(str(e))
        error_str = ERROR_TEMPLATES.get(
            error_type, ERROR_TEMPLATES["generic"]
        ).format(tool_label=tool_label, entity="")

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "tool_label": tool_label,
            "args": tool_args,
            "result": {"error": str(e)},
            "formatted_result": "",
            "error": error_str,
            "error_type": error_type,
            "success": False,
        }

        return {
            "tool_results": [tool_result],
            "step_count": step_count + 1,
            "_planned_tool": None,
            "_planned_args": None,
        }


# =============================================================================
# Node 5: RESULT_CLASSIFY (LLM + Outlines, T=0.0)
# =============================================================================


def result_classify(state: AgentState, model: DocGemma) -> dict:
    """Classify tool result quality for routing decisions.

    Errors are classified deterministically (fast-path).
    Successful results use LLM + Outlines (94% accuracy, Part III Section 29).
    """
    tool_results = state.get("tool_results", [])
    if not tool_results:
        return {
            "last_result_classification": "no_results",
            "last_result_summary": "No tool results available",
        }

    last = tool_results[-1]

    # Fast-path: errors classified deterministically
    if not last.get("success"):
        error_type = last.get("error_type", "generic")
        if error_type in ("timeout", "rate_limit", "server_error"):
            return {
                "last_result_classification": "error_retryable",
                "last_result_summary": last.get("error", "Retryable error"),
            }
        return {
            "last_result_classification": "error_fatal",
            "last_result_summary": last.get("error", "Fatal error"),
        }

    # LLM classification for successful results
    tool_label = last.get("tool_label", last.get("tool_name", "Unknown"))
    formatted = last.get("formatted_result", str(last.get("result", {})))

    # Truncate the formatted result for the LLM prompt, but keep JSON valid.
    # If it's valid JSON, re-serialize with truncated string values;
    # otherwise fall back to plain text truncation.
    classify_result_text = formatted
    try:
        parsed = json.loads(formatted)
        if isinstance(parsed, dict):
            parsed = {
                k: (v[:400] + "..." if isinstance(v, str) and len(v) > 400 else v)
                for k, v in parsed.items()
                if v is not None
            }
            classify_result_text = json.dumps(parsed, default=str)
    except (json.JSONDecodeError, TypeError):
        classify_result_text = _truncate(formatted, 500)

    prompt = RESULT_CLASSIFY_PROMPT.format(
        user_query=state.get("user_query", ""),
        task_summary=state.get("task_summary", ""),
        thinking_section=_thinking_context_section(state),
        tool_label=tool_label,
        formatted_tool_result=classify_result_text,
    )

    result = model.generate_outlines(
        prompt,
        ResultAssessment,
        temperature=TEMPERATURE["result_classify"],
        max_new_tokens=MAX_TOKENS["result_classify"],
    )

    logger.info(
        f"[RESULT_CLASSIFY] quality={result.quality}, "
        f"summary={_truncate(result.brief_summary)}"
    )

    return {
        "last_result_classification": result.quality,
        "last_result_summary": result.brief_summary,
    }


# =============================================================================
# Node 7: SYNTHESIZE (LLM free-form, T=0.5, max_tokens=256)
# =============================================================================


async def synthesize(
    state: AgentState,
    model: DocGemma,
    stream_callback: StreamCallback = None,
) -> dict:
    """Generate final clinician-facing response.

    Direct route: lightweight DIRECT_CHAT_PROMPT.
    Tool route: full SYNTHESIZE_SYSTEM_PROMPT + assembled context.

    T=0.5, max_tokens=256 (validated optimum, Part IV Section 43/46).
    No thinking prefix (13% empty output risk, Part IV Section 42).
    """
    query = state.get("user_query", "")
    history = state.get("conversation_history", [])
    intent = state.get("intent", "DIRECT")
    tool_results = state.get("tool_results", [])

    tools_enabled = state.get("tool_calling_enabled", True)

    # ── Direct route: lightweight conversational prompt ──
    if intent == "DIRECT" and not tool_results:
        context = _patient_context_section(state)
        if state.get("image_findings"):
            context += f"\nAttached image findings:\n{state['image_findings']}\n"
        if not tools_enabled:
            context += "\nNote: Tool calling is disabled. Answer using only the information above.\n"

        prompt = DIRECT_CHAT_PROMPT.format(
            user_query=query,
            thinking_section=_thinking_context_section(state),
            patient_context_section=context,
        )

        if stream_callback:
            chunks: list[str] = []
            async for chunk in model.generate_stream(
                prompt,
                max_new_tokens=MAX_TOKENS["synthesize"],
                do_sample=True,
                temperature=TEMPERATURE["synthesize"],
                messages=history,
            ):
                await stream_callback(chunk)
                chunks.append(chunk)
            response = "".join(chunks)
        else:
            response = model.generate(
                prompt,
                max_new_tokens=MAX_TOKENS["synthesize"],
                do_sample=True,
                temperature=TEMPERATURE["synthesize"],
                messages=history,
            )

        return {
            "final_response": response,
            "model_thinking": model.last_thinking_text,
        }

    # ── Tool/complex route: full synthesis ──

    # Build tool results section
    tool_results_section = ""
    if tool_results:
        sections = []
        for r in tool_results:
            if r.get("success"):
                sections.append(_format_tool_result(r))
        if sections:
            tool_results_section = (
                "\n\nTool findings:\n" + "\n\n".join(sections)
            )

    # Build error section
    error_section = ""
    error_messages = state.get("error_messages", [])
    if error_messages:
        error_section = (
            "\n\nUnavailable information:\n"
            + _format_error_for_synthesis(error_messages)
        )

    # Build image section
    image_section = ""
    image_findings = state.get("image_findings")
    if image_findings:
        image_section = f"\n\nImage analysis:\n{image_findings}"

    # Build clarification section
    clarification_section = ""
    clarification = state.get("clarification_request")
    if clarification:
        clarification_section = f"\n\nClarification needed:\n{clarification}"

    # Build tool-calling status note
    tools_note = ""
    if not tools_enabled:
        tools_note = "\n\nNote: Tool calling is disabled. Answer using only the information above."

    user_prompt = SYNTHESIZE_USER_TEMPLATE.format(
        user_query=query,
        task_summary=state.get("task_summary", ""),
        thinking_section=_thinking_context_section(state),
        patient_context_section=_patient_context_section(state),
        image_section=image_section,
        tool_results_section=tool_results_section,
        error_section=error_section,
        clarification_section=clarification_section,
    ) + tools_note

    # Prepend synthesis guidelines to user prompt
    full_prompt = SYNTHESIZE_SYSTEM_PROMPT + "\n\n" + user_prompt

    if stream_callback:
        chunks = []
        async for chunk in model.generate_stream(
            full_prompt,
            max_new_tokens=MAX_TOKENS["synthesize"],
            do_sample=True,
            temperature=TEMPERATURE["synthesize"],
            messages=history,
        ):
            await stream_callback(chunk)
            chunks.append(chunk)
        response = "".join(chunks)
    else:
        response = model.generate(
            full_prompt,
            max_new_tokens=MAX_TOKENS["synthesize"],
            do_sample=True,
            temperature=TEMPERATURE["synthesize"],
            messages=history,
        )

    return {
        "final_response": response,
        "model_thinking": model.last_thinking_text,
    }


# =============================================================================
# Routing Functions (used as conditional edges in graph.py)
# =============================================================================


def route_after_tool_select(state: dict) -> str:
    """Route after tool selection.

    If the model selected "none" (no applicable tool), skip tool execution
    and go straight to synthesize.  Otherwise proceed to tool_execute.
    """
    if state.get("current_tool") == "none":
        logger.info("[ROUTE] tool_select → synthesize (no applicable tool)")
        return "synthesize"
    logger.info("[ROUTE] tool_select → tool_execute")
    return "tool_execute"


def route_after_intent(state: dict) -> str:
    """Route after intent classification.

    DIRECT → synthesize (2 LLM calls total).
    TOOL_NEEDED → tool_select (enters reactive tool loop).
    """
    intent = state.get("intent", "DIRECT")
    if intent == "DIRECT":
        logger.info("[ROUTE] intent_classify → synthesize (DIRECT)")
        return "synthesize"
    logger.info("[ROUTE] intent_classify → tool_select (TOOL_NEEDED)")
    return "tool_select"


def route_after_result_classify(state: dict) -> str:
    """Deterministic router after result classification.

    All "what to do next" decisions in code, not LLM (V3 spec Section 6).
    Task-pattern matching for deterministic termination (Section 11).
    Safety valves: MAX_STEPS, duplicate detection, single-tool default.
    """
    classification = state.get("last_result_classification", "")

    # Error → synthesize directly (no retry loop)
    if classification.startswith("error"):
        # Append pre-formatted error from the last tool result so synthesis has context
        tool_results = state.get("tool_results", [])
        if tool_results:
            last = tool_results[-1]
            error_msg = last.get("error") or ERROR_TEMPLATES["generic"].format(
                tool_label=last.get("tool_label", "Unknown"), entity=""
            )
            error_messages = list(state.get("error_messages", []))
            error_messages.append(error_msg)
            state["error_messages"] = error_messages
        logger.info(
            f"[ROUTE] result_classify → synthesize ({classification})"
        )
        return "synthesize"

    query = state.get("user_query", "")
    tool_results = state.get("tool_results", [])
    step_count = state.get("step_count", 0)

    # User clarification needed → synthesize
    if _needs_user_clarification(tool_results):
        logger.info("[ROUTE] result_classify → synthesize (clarification needed)")
        return "synthesize"

    # Safety valve: max steps
    if step_count >= MAX_STEPS:
        logger.info(f"[ROUTE] result_classify → synthesize (max steps {MAX_STEPS})")
        return "synthesize"

    # Duplicate tool call detection
    current_tool = state.get("current_tool")
    current_args = state.get("current_args", {})
    if current_tool and _is_duplicate_tool_call(
        current_tool, current_args, tool_results[:-1] if tool_results else []
    ):
        logger.info("[ROUTE] result_classify → synthesize (duplicate tool call)")
        return "synthesize"

    # Task pattern fully satisfied → synthesize
    if _task_pattern_satisfied(query, tool_results):
        logger.info("[ROUTE] result_classify → synthesize (task pattern satisfied)")
        return "synthesize"

    # Check if a pattern was matched but NOT yet satisfied → need more tools
    completed_tools = {r["tool_name"] for r in tool_results if r.get("success")}
    for pattern in TASK_PATTERNS.values():
        if _match_task_pattern(query, pattern):
            required = pattern["requires"]
            if not required.issubset(completed_tools):
                logger.info(
                    f"[ROUTE] result_classify → tool_select "
                    f"(pattern needs: {required - completed_tools})"
                )
                return "tool_select"

    # No pattern matched — single-tool default: synthesize after first good result
    logger.info("[ROUTE] result_classify → synthesize (single-tool default)")
    return "synthesize"


