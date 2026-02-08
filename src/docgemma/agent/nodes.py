"""Agent node implementations (v2: 4-way triage architecture).

18 nodes: image_detection, clinical_context_assembler, triage_router,
fast_tool_validate, fast_fix_args, fast_execute, fast_check,
thinking_mode, extract_tool_needs, reasoning_execute, reasoning_continuation,
decompose_intent, plan_tool, loop_validate, loop_fix_args, loop_execute,
assess_result, error_handler, synthesize_response.
"""

from __future__ import annotations

import functools
import json
import logging
import time
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar

# Callback type for streaming tokens during generation
StreamCallback = Callable[[str], Awaitable[None]] | None

from .prompts import (
    CLARIFICATION_PROMPT,
    EXTRACT_TOOL_NEEDS_PROMPT,
    FIX_ARGS_PROMPT,
    REASONING_CONTINUATION_PROMPT,
    SYNTHESIS_PROMPT,
    TEMPERATURE,
    THINKING_PROMPT,
    TRIAGE_PROMPT,
    get_decompose_prompt,
    get_plan_prompt,
)
from .schemas import (
    DecomposedIntentV2,
    ExtractedToolNeeds,
    FixedArgs,
    ThinkingOutput,
    ToolCallV2,
    TriageDecision,
)
from .state import DocGemmaState, Subtask, ToolResult
from ..tools.registry import get_tools_for_prompt

if TYPE_CHECKING:
    from ..model import DocGemma

logger = logging.getLogger(__name__)

# =============================================================================
# Timing Decorator
# =============================================================================

P = ParamSpec("P")
T = TypeVar("T")


def timed_node(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to log elapsed time for node execution."""

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[NODE] {func.__name__} starting...")
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[NODE] {func.__name__} completed in {elapsed_ms:.1f}ms")

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[NODE] {func.__name__} starting...")
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[NODE] {func.__name__} completed in {elapsed_ms:.1f}ms")

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    return sync_wrapper  # type: ignore


# =============================================================================
# Constants
# =============================================================================

MAX_ITERATIONS_PER_SUBTASK = 3
MAX_TOOL_RETRIES = 2
MAX_SUBTASKS = 5
MAX_FAST_RETRIES = 2

SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/dicom",
    "application/dicom",
}


# =============================================================================
# Helpers
# =============================================================================

def _truncate_for_log(obj: dict, max_len: int = 200) -> str:
    """Truncate object representation for logging."""
    try:
        s = json.dumps(obj, default=str)
    except Exception:
        s = str(obj)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _format_tool_results(results: list[ToolResult]) -> str:
    """Format tool results for synthesis prompt."""
    if not results:
        return "No tools were called."

    lines = []
    for r in results:
        status = "SUCCESS" if r["success"] else "FAILED"
        lines.append(f"[{r['tool_name']}] ({status})")
        if r["success"]:
            result_str = str(r["result"])
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            lines.append(f"  {result_str}")
        else:
            lines.append(f"  Error: {r['result'].get('error', 'Unknown error')}")
    return "\n".join(lines)


def _summarize_recent_turns(
    history: list[dict], max_turns: int = 3
) -> str:
    """Summarize recent conversation turns for context."""
    if not history:
        return ""
    recent = history[-max_turns * 2 :]  # 2 messages per turn (user+assistant)
    lines = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if len(content) > 100:
            content = content[:100] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _validate_tool_call(
    tool_name: str | None, args: dict, state: DocGemmaState
) -> tuple[bool, str]:
    """Validate a tool call before execution."""
    if not tool_name or tool_name == "none":
        return False, "No tool specified"
    if tool_name in (
        "get_patient_chart",
        "add_allergy",
        "prescribe_medication",
        "save_clinical_note",
    ):
        if not args.get("patient_id"):
            return False, "No patient_id — use search_patient first"
    if tool_name == "check_drug_interactions":
        drug_list = args.get("drug_list", "")
        if not drug_list or "," not in drug_list:
            return False, "Drug interaction check needs at least 2 comma-separated drugs"
    if tool_name == "analyze_medical_image" and not state.get("image_data"):
        return False, "No image attached"
    return True, ""


def _collect_args_from_model(result) -> dict:
    """Collect non-None argument fields from a ToolCallV2 or FixedArgs model result."""
    arguments = {}
    for field_name in (
        "query", "drug_name", "drug_list", "patient_id", "name", "dob",
        "substance", "reaction", "severity", "medication_name", "dosage",
        "frequency", "note_text", "note_type",
    ):
        val = getattr(result, field_name, None)
        if val is not None:
            arguments[field_name] = val
    return arguments


async def _execute_tool_impl(
    state: DocGemmaState, tool_executor
) -> DocGemmaState:
    """Shared tool execution logic for fast_execute, reasoning_execute, loop_execute."""
    tool_name = state.get("_planned_tool")
    tool_args = state.get("_planned_args", {})

    if not tool_name or tool_name == "none":
        logger.info("[TOOL] No tool needed, skipping execution")
        return {
            **state,
            "last_result_status": "success",
            "_planned_tool": None,
            "_planned_args": None,
        }

    # Inject image_data from state for vision tool
    if tool_name == "analyze_medical_image":
        image_data = state.get("image_data")
        if image_data:
            tool_args = {**tool_args, "image_data": image_data}

    logger.info(f"[TOOL] Executing: {tool_name}")
    logger.info(f"[TOOL] Arguments: {_truncate_for_log(tool_args)}")

    start = time.perf_counter()
    try:
        result = await tool_executor(tool_name, tool_args)
        elapsed_ms = (time.perf_counter() - start) * 1000

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": result,
            "success": not result.get("error"),
        }

        tool_results = list(state.get("tool_results", []))
        tool_results.append(tool_result)

        status = "success" if tool_result["success"] else "error"

        logger.info(
            f"[TOOL] {tool_name} completed in {elapsed_ms:.1f}ms - {status.upper()}"
        )
        logger.info(f"[TOOL] Result: {_truncate_for_log(result)}")

        return {
            **state,
            "tool_results": tool_results,
            "last_result_status": status,
            "_planned_tool": None,
            "_planned_args": None,
        }

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000

        tool_result: ToolResult = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": {"error": str(e)},
            "success": False,
        }
        tool_results = list(state.get("tool_results", []))
        tool_results.append(tool_result)

        logger.error(f"[TOOL] {tool_name} failed in {elapsed_ms:.1f}ms - ERROR: {e}")

        return {
            **state,
            "tool_results": tool_results,
            "last_result_status": "error",
            "_planned_tool": None,
            "_planned_args": None,
        }


# =============================================================================
# Node 1: Image Detection (Pure Code)
# =============================================================================


@timed_node
def image_detection(state: DocGemmaState) -> DocGemmaState:
    """Detect if medical images are attached to the request."""
    image_present = state.get("image_data") is not None
    return {**state, "image_present": image_present}


# =============================================================================
# Node 2: Clinical Context Assembler (Pure Code)
# =============================================================================


@timed_node
def clinical_context_assembler(state: DocGemmaState) -> DocGemmaState:
    """Gather clinical context before triage."""
    context = {
        "user_input": state["user_input"],
        "image_present": state.get("image_present", False),
        "conversation_summary": _summarize_recent_turns(
            state.get("conversation_history", []), max_turns=3
        ),
    }
    return {**state, "clinical_context": context}


# =============================================================================
# Node 3: Triage Router (LLM + Outlines, 4-way)
# =============================================================================


@timed_node
def triage_router(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """Route query to direct/lookup/reasoning/multi_step."""
    # Image attached = always multi_step (needs analyze_medical_image + reasoning)
    if state.get("image_present"):
        return {
            **state,
            "triage_route": "multi_step",
            "triage_tool": None,
            "triage_query": None,
        }

    context = state.get("clinical_context") or {}
    context_line = ""
    conv_summary = context.get("conversation_summary", "")
    if conv_summary:
        context_line = f"Recent conversation:\n{conv_summary}"

    prompt = TRIAGE_PROMPT.format(
        user_input=state["user_input"],
        context_line=context_line,
    )
    result = model.generate_outlines(
        prompt, TriageDecision, temperature=TEMPERATURE["triage_router"]
    )

    return {
        **state,
        "triage_route": result.route,
        "triage_tool": result.tool if result.route == "lookup" else None,
        "triage_query": result.query if result.route == "lookup" else None,
    }


# =============================================================================
# Node 4: Fast Tool Validate (Pure Code — LOOKUP path)
# =============================================================================


@timed_node
def fast_tool_validate(state: DocGemmaState) -> DocGemmaState:
    """Validate triage-provided tool call for LOOKUP path."""
    tool = state.get("triage_tool")
    query = state.get("triage_query", "")
    args = {"query": query} if query else {}

    # For drug safety, map query to drug_name
    if tool == "check_drug_safety" and query:
        args["drug_name"] = query
    elif tool == "check_drug_interactions" and query:
        args["drug_list"] = query
    elif tool == "search_patient" and query:
        args["name"] = query

    valid, error = _validate_tool_call(tool, args, state)
    if valid:
        return {
            **state,
            "_planned_tool": tool,
            "_planned_args": args,
            "validation_error": None,
        }
    return {**state, "validation_error": error}


# =============================================================================
# Node 5: Fast Fix Args (LLM + Outlines — LOOKUP path)
# =============================================================================


@timed_node
def fast_fix_args(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """LLM reformulates args for LOOKUP path after validation failure."""
    tool = state.get("triage_tool", "none")
    query = state.get("triage_query", "")

    prompt = FIX_ARGS_PROMPT.format(
        tool_name=tool,
        previous_args=json.dumps({"query": query}),
        validation_error=state.get("validation_error", ""),
    )
    result = model.generate_outlines(
        prompt, FixedArgs, max_new_tokens=128, temperature=TEMPERATURE["fix_args"]
    )

    fixed = _collect_args_from_model(result)
    return {
        **state,
        "_planned_tool": tool,
        "_planned_args": fixed,
        "validation_error": None,
    }


# =============================================================================
# Node 6: Fast Execute (Async — LOOKUP path)
# =============================================================================


@timed_node
async def fast_execute(state: DocGemmaState, tool_executor) -> DocGemmaState:
    """Execute tool for LOOKUP path."""
    return await _execute_tool_impl(state, tool_executor)


# =============================================================================
# Node 7: Fast Check (Pure Code — LOOKUP path)
# =============================================================================


@timed_node
def fast_check(state: DocGemmaState) -> DocGemmaState:
    """Check LOOKUP result: success -> synthesize, error -> retry or synthesize."""
    status = state.get("last_result_status", "success")
    retries = state.get("tool_retries", 0)

    if status == "success":
        return {**state, "last_result_status": "done"}

    # Error path
    if retries < MAX_FAST_RETRIES:
        return {**state, "tool_retries": retries + 1, "last_result_status": "error"}

    # Max retries exceeded, proceed to synthesis with partial results
    logger.warning("[FAST_CHECK] Max retries exceeded, proceeding to synthesis")
    return {**state, "last_result_status": "done"}


# =============================================================================
# Node 8: Thinking Mode (LLM + Outlines — REASONING path)
# =============================================================================


@timed_node
def thinking_mode(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """Generate reasoning for complex queries."""
    context = state.get("clinical_context") or {}
    context_line = ""
    conv_summary = context.get("conversation_summary", "")
    if conv_summary:
        context_line = f"Context:\n{conv_summary}"

    prompt = THINKING_PROMPT.format(
        user_input=state["user_input"],
        context_line=context_line,
    )
    result = model.generate_outlines(
        prompt,
        ThinkingOutput,
        max_new_tokens=1024,
        temperature=TEMPERATURE["thinking_mode"],
    )
    return {**state, "reasoning": result.reasoning}


# =============================================================================
# Node 9: Extract Tool Needs (LLM + Outlines — REASONING path)
# =============================================================================


@timed_node
def extract_tool_needs(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """From reasoning chain, identify if a tool call would help."""
    tools = get_tools_for_prompt()
    prompt = EXTRACT_TOOL_NEEDS_PROMPT.format(
        reasoning=state.get("reasoning", ""),
        user_input=state["user_input"],
        tools=tools,
    )
    result = model.generate_outlines(
        prompt,
        ExtractedToolNeeds,
        max_new_tokens=128,
        temperature=TEMPERATURE["extract_tool_needs"],
    )

    if result.needs_tool and result.tool and result.tool != "none":
        tool_needs = {"tool": result.tool, "query": result.query or ""}
        # Prepare args for execution
        args = {}
        if result.query:
            args["query"] = result.query
        if result.tool == "check_drug_safety" and result.query:
            args["drug_name"] = result.query
        elif result.tool == "check_drug_interactions" and result.query:
            args["drug_list"] = result.query
        elif result.tool == "search_patient" and result.query:
            args["name"] = result.query

        return {
            **state,
            "reasoning_tool_needs": tool_needs,
            "_planned_tool": result.tool,
            "_planned_args": args,
        }

    return {
        **state,
        "reasoning_tool_needs": None,
        "_planned_tool": None,
        "_planned_args": None,
    }


# =============================================================================
# Node 10: Reasoning Execute (Async — REASONING path)
# =============================================================================


@timed_node
async def reasoning_execute(state: DocGemmaState, tool_executor) -> DocGemmaState:
    """Execute tool for REASONING path."""
    return await _execute_tool_impl(state, tool_executor)


# =============================================================================
# Node 11: Reasoning Continuation (LLM streaming — REASONING path)
# =============================================================================


@timed_node
async def reasoning_continuation(
    state: DocGemmaState,
    model: DocGemma,
    stream_callback: StreamCallback = None,
) -> DocGemmaState:
    """Continue reasoning over tool results."""
    tool_results = state.get("tool_results", [])
    tool_result_text = _format_tool_results(tool_results)

    prompt = REASONING_CONTINUATION_PROMPT.format(
        user_input=state["user_input"],
        reasoning=state.get("reasoning", ""),
        tool_result=tool_result_text,
    )

    if stream_callback:
        chunks: list[str] = []
        async for chunk in model.generate_stream(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=TEMPERATURE["reasoning_continuation"],
        ):
            await stream_callback(chunk)
            chunks.append(chunk)
        text = "".join(chunks)
    else:
        text = model.generate(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=TEMPERATURE["reasoning_continuation"],
        )
    return {**state, "reasoning_continuation": text}


# =============================================================================
# Node 12: Decompose Intent (LLM + Outlines — MULTI_STEP path)
# =============================================================================


@timed_node
def decompose_intent(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """Decompose complex query into subtasks (flat structure, max 5)."""
    prompt = get_decompose_prompt(
        user_input=state["user_input"],
        reasoning=state.get("reasoning", ""),
    )

    result = model.generate_outlines(
        prompt,
        DecomposedIntentV2,
        max_new_tokens=512,
        temperature=TEMPERATURE["decompose_intent"],
    )

    # Handle clarification needed
    if result.needs_clarification:
        return {
            **state,
            "needs_user_input": True,
            "missing_info": result.clarification_question,
            "subtasks": [],
        }

    # Convert flat fields to subtask list
    subtasks: list[Subtask] = []

    for i in range(1, MAX_SUBTASKS + 1):
        subtask_text = getattr(result, f"subtask_{i}", None)
        tool = getattr(result, f"tool_{i}", None)
        if subtask_text and tool:
            subtasks.append(
                {
                    "intent": subtask_text,
                    "requires_tool": tool,
                    "context": state["user_input"],
                }
            )

    return {
        **state,
        "subtasks": subtasks,
        "current_subtask_index": 0,
        "tool_results": [],
        "loop_iterations": 0,
        "tool_retries": 0,
    }


# =============================================================================
# Node 13: Plan Tool (LLM + Outlines — MULTI_STEP loop)
# =============================================================================


@timed_node
def plan_tool(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """Select tool for current subtask."""
    idx = state.get("current_subtask_index", 0)
    subtasks = state.get("subtasks", [])

    if not subtasks or idx >= len(subtasks):
        return {**state, "last_result_status": "done"}

    subtask = subtasks[idx]

    prompt = get_plan_prompt(
        intent=subtask["intent"],
        suggested_tool=subtask.get("requires_tool", "none"),
    )

    result = model.generate_outlines(
        prompt,
        ToolCallV2,
        max_new_tokens=256,
        temperature=TEMPERATURE["plan_tool"],
    )

    arguments = _collect_args_from_model(result)

    return {
        **state,
        "_planned_tool": result.tool_name,
        "_planned_args": arguments,
    }


# =============================================================================
# Node 14: Loop Validate (Pure Code — MULTI_STEP loop)
# =============================================================================


@timed_node
def loop_validate(state: DocGemmaState) -> DocGemmaState:
    """Validate planned tool call in agentic loop."""
    tool = state.get("_planned_tool")
    args = state.get("_planned_args", {})
    valid, error = _validate_tool_call(tool, args, state)
    if valid:
        return {**state, "validation_error": None}
    return {**state, "validation_error": error}


# =============================================================================
# Node 15: Loop Fix Args (LLM + Outlines — MULTI_STEP loop)
# =============================================================================


@timed_node
def loop_fix_args(state: DocGemmaState, model: DocGemma) -> DocGemmaState:
    """LLM reformulates args after loop validation failure."""
    tool = state.get("_planned_tool", "none")
    args = state.get("_planned_args", {})

    prompt = FIX_ARGS_PROMPT.format(
        tool_name=tool,
        previous_args=json.dumps(args, default=str),
        validation_error=state.get("validation_error", ""),
    )
    result = model.generate_outlines(
        prompt, FixedArgs, max_new_tokens=128, temperature=TEMPERATURE["fix_args"]
    )

    fixed = _collect_args_from_model(result)
    return {
        **state,
        "_planned_args": fixed,
        "validation_error": None,
    }


# =============================================================================
# Node 16: Loop Execute (Async — MULTI_STEP loop)
# =============================================================================


@timed_node
async def loop_execute(state: DocGemmaState, tool_executor) -> DocGemmaState:
    """Execute tool in agentic loop."""
    return await _execute_tool_impl(state, tool_executor)


# =============================================================================
# Node 17: Assess Result (Pure Code — MULTI_STEP loop)
# =============================================================================


@timed_node
def assess_result(state: DocGemmaState) -> DocGemmaState:
    """Assess tool result and decide next action."""
    status = state.get("last_result_status", "success")
    iterations = state.get("loop_iterations", 0)
    idx = state.get("current_subtask_index", 0)
    subtasks = state.get("subtasks", [])

    if status == "error":
        return {**state}  # error_handler will decide strategy

    if status == "success":
        # Check for more subtasks
        if idx < len(subtasks) - 1:
            return {
                **state,
                "current_subtask_index": idx + 1,
                "loop_iterations": 0,
                "tool_retries": 0,
                "last_result_status": "continue",
            }
        # All subtasks done
        return {**state, "last_result_status": "done"}

    if status == "needs_more_action":
        if iterations < MAX_ITERATIONS_PER_SUBTASK:
            return {
                **state,
                "loop_iterations": iterations + 1,
                "last_result_status": "continue",
            }
        # Max iterations, move on
        return {**state, "last_result_status": "done"}

    if status == "needs_user_input":
        return {**state, "needs_user_input": True, "last_result_status": "done"}

    return {**state, "last_result_status": "done"}


# =============================================================================
# Node 18: Error Handler (Pure Code — MULTI_STEP loop)
# =============================================================================


@timed_node
def error_handler(state: DocGemmaState) -> DocGemmaState:
    """Classify error and select recovery strategy."""
    tool_results = state.get("tool_results", [])
    retries = state.get("tool_retries", 0)

    error = ""
    if tool_results:
        last_result = tool_results[-1]
        error = str(last_result.get("result", {}).get("error", ""))

    # Transient errors: retry same
    if any(
        keyword in error.lower()
        for keyword in ("timeout", "network", "connection", "rate limit")
    ):
        if retries < MAX_TOOL_RETRIES:
            return {
                **state,
                "error_strategy": "retry_same",
                "tool_retries": retries + 1,
            }

    # Max retries: skip subtask
    if retries >= MAX_TOOL_RETRIES:
        idx = state.get("current_subtask_index", 0)
        subtasks = state.get("subtasks", [])
        if idx < len(subtasks) - 1:
            return {
                **state,
                "error_strategy": "skip_subtask",
                "current_subtask_index": idx + 1,
                "loop_iterations": 0,
                "tool_retries": 0,
            }
        return {
            **state,
            "error_strategy": "skip_subtask",
            "last_result_status": "done",
        }

    # Otherwise: retry with reformulated args
    return {
        **state,
        "error_strategy": "retry_reformulate",
        "tool_retries": retries + 1,
    }


# =============================================================================
# Node 19: Synthesize Response (LLM streaming — terminal, all routes)
# =============================================================================


@timed_node
async def synthesize_response(
    state: DocGemmaState,
    model: DocGemma,
    stream_callback: StreamCallback = None,
) -> DocGemmaState:
    """Generate final response from accumulated context. All routes converge here."""
    # Handle clarification request
    if state.get("needs_user_input"):
        prompt = CLARIFICATION_PROMPT.format(
            user_input=state["user_input"],
            missing_info=state.get("missing_info", "specific details"),
        )
        if stream_callback:
            chunks: list[str] = []
            async for chunk in model.generate_stream(
                prompt,
                max_new_tokens=256,
                do_sample=True,
                temperature=TEMPERATURE["clarification"],
            ):
                await stream_callback(chunk)
                chunks.append(chunk)
            response = "".join(chunks)
        else:
            response = model.generate(
                prompt,
                max_new_tokens=256,
                do_sample=True,
                temperature=TEMPERATURE["clarification"],
            )
        return {**state, "final_response": response}

    # Build context-aware prompt
    reasoning = state.get("reasoning") or ""
    reasoning_cont = state.get("reasoning_continuation") or ""
    combined_reasoning = reasoning
    if reasoning_cont:
        combined_reasoning = f"{reasoning}\n\n{reasoning_cont}"

    reasoning_line = ""
    if combined_reasoning:
        reasoning_line = f"Reasoning:\n{combined_reasoning}"

    tool_results = state.get("tool_results", [])
    tool_results_line = ""
    if tool_results:
        tool_results_line = f"Tool findings:\n{_format_tool_results(tool_results)}"

    prompt = SYNTHESIS_PROMPT.format(
        user_input=state["user_input"],
        reasoning_line=reasoning_line,
        tool_results_line=tool_results_line,
    )

    if stream_callback:
        chunks = []
        async for chunk in model.generate_stream(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=TEMPERATURE["synthesize_response"],
        ):
            await stream_callback(chunk)
            chunks.append(chunk)
        response = "".join(chunks)
    else:
        response = model.generate(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=TEMPERATURE["synthesize_response"],
        )
    return {**state, "final_response": response}
