"""LangGraph workflow definition for DocGemma v3 agent.

7-node architecture with binary intent classification and reactive tool loop:

  INPUT_ASSEMBLY → INTENT_CLASSIFY
    → DIRECT    → SYNTHESIZE → END
    → TOOL_NEEDED → TOOL_SELECT → TOOL_EXECUTE → RESULT_CLASSIFY
                     ↑              → [error] → ERROR_HANDLER → [retry → TOOL_EXECUTE | skip → SYNTHESIZE]
                     └──────────────← [more tools needed]
                                    → [done] → SYNTHESIZE → END

Grounded in 856 experiments on MedGemma 4B (see MEDGEMMA_PROMPTING_GUIDE.md).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from .nodes import (
    StreamCallback,
    error_handler,
    input_assembly,
    intent_classify,
    result_classify,
    route_after_error_handler,
    route_after_intent,
    route_after_result_classify,
    synthesize,
    tool_execute,
    tool_select,
)
from .prompts import TOOL_CLINICAL_LABELS, WRITE_TOOLS
from .state import AgentState
from ..tools.registry import execute_tool as registry_execute_tool

if TYPE_CHECKING:
    from ..model import DocGemma

logger = logging.getLogger(__name__)


# =============================================================================
# Status message pools (human-readable, randomized for natural feel)
# =============================================================================

_TOOL_STATUS_POOLS: dict[str, list[str]] = {
    "check_drug_safety": [
        "Checking FDA safety database...",
        "Reviewing drug safety profile...",
        "Looking up safety information...",
    ],
    "check_drug_interactions": [
        "Checking drug interactions...",
        "Screening for interactions...",
        "Cross-referencing medications...",
    ],
    "search_medical_literature": [
        "Searching medical literature...",
        "Reviewing published research...",
        "Consulting PubMed...",
    ],
    "find_clinical_trials": [
        "Searching clinical trials...",
        "Looking up active trials...",
        "Checking trial registries...",
    ],
    "search_patient": [
        "Searching patient records...",
        "Looking up patient information...",
    ],
    "get_patient_chart": [
        "Retrieving patient chart...",
        "Loading clinical history...",
    ],
    "add_allergy": [
        "Documenting allergy...",
        "Recording allergy information...",
    ],
    "prescribe_medication": [
        "Processing prescription...",
        "Preparing medication order...",
    ],
    "save_clinical_note": [
        "Saving clinical note...",
        "Recording clinical note...",
    ],
    "analyze_medical_image": [
        "Analyzing medical image...",
        "Reviewing image findings...",
    ],
}

_STATUS_POOLS: dict[str, list[str]] = {
    "analyzing_query": [
        "Analyzing query...",
        "Understanding your question...",
        "Processing your question...",
    ],
    "composing_response": [
        "Composing response...",
        "Preparing response...",
        "Synthesizing findings...",
    ],
    "selecting_tool": [
        "Selecting the right tool...",
        "Determining approach...",
    ],
    "processing_results": [
        "Processing results...",
        "Reviewing results...",
        "Interpreting findings...",
    ],
    "handling_error": [
        "Handling error...",
        "Working around an issue...",
        "Recovering from error...",
    ],
    "retrying": [
        "Retrying...",
        "Trying again...",
    ],
}


def _pick(pool_key: str) -> str:
    """Pick a random status text from a pool."""
    return random.choice(_STATUS_POOLS[pool_key])


def _pick_tool(tool_name: str) -> str:
    """Pick a random status text for a tool."""
    pool = _TOOL_STATUS_POOLS.get(tool_name)
    if pool:
        return random.choice(pool)
    return f"Using {tool_name.replace('_', ' ')}..."


# =============================================================================
# GraphConfig — interface consumed by agent_runner.py
# =============================================================================


@dataclass(frozen=True)
class GraphConfig:
    """Everything the API layer needs to know about the graph topology.

    The graph author fills this in alongside ``build_graph()``.  The API layer
    (``agent_runner.py``) consumes it without importing any node names.
    """

    # Node names to interrupt before (for tool approval). Empty = no approval.
    interrupt_before: list[str]

    # Given state dict at interrupt, return (tool_name, tool_args, intent_text).
    # Return (None, {}, "") if interrupt should be auto-resumed (no-op tool).
    extract_tool_proposal: Callable[[dict], tuple[str | None, dict, str]]

    # Given state dict + rejection reason, return state-update dict to apply
    # before resuming after rejection.
    build_rejection_update: Callable[[dict, str | None], dict]

    # Set of node names that produce the final response.
    terminal_nodes: frozenset[str]

    # State key that carries the final response text.
    final_response_key: str  # e.g. "final_response"

    # Factory: (user_input, image_data, conversation_history, **kwargs) -> initial state dict.
    make_initial_state: Callable[..., dict]

    # (node_name, state_update) -> status text or None.
    get_status_text: Callable[[str, dict], str | None] | None

    # node_id -> human-readable label.
    node_labels: dict[str, str]

    # (full_state, node_durations) -> ClinicalTrace or None.
    build_clinical_trace: Callable[[dict, dict[str, float]], Any] | None


# =============================================================================
# GraphConfig helpers (private — consumed only by GRAPH_CONFIG below)
# =============================================================================


def _extract_tool_proposal(state: dict) -> tuple[str | None, dict, str]:
    """Read the planned tool from interrupt state.

    Returns (None, {}, "") for no-op or read-only tools so the graph
    auto-resumes without user approval.  Only write operations (allergy,
    prescription, clinical note) surface a ToolApprovalRequest.
    """
    planned_tool = state.get("_planned_tool")
    planned_args = state.get("_planned_args", {})

    if not planned_tool or planned_tool == "none":
        return (None, {}, "")

    # Read-only tools auto-approve
    if planned_tool not in WRITE_TOOLS:
        return (None, {}, "")

    intent = state.get("user_query", "")
    return (planned_tool, planned_args, intent)


def _build_rejection_update(state: dict, reason: str | None) -> dict:
    """Build state update dict for a rejected tool."""
    return {
        "_planned_tool": None,
        "_planned_args": None,
        "tool_results": [
            {
                "tool_name": state.get("_planned_tool", "unknown"),
                "tool_label": TOOL_CLINICAL_LABELS.get(
                    state.get("_planned_tool", ""), "Unknown"
                ),
                "args": state.get("_planned_args", {}),
                "result": {"rejected": True, "reason": reason or "User rejected"},
                "formatted_result": "",
                "error": reason or "User rejected",
                "error_type": None,
                "success": False,
            }
        ],
    }


def _make_initial_state(
    user_input: str,
    image_data: bytes | None,
    conversation_history: list[dict] | None,
    *,
    patient_id: str | None = None,
    tool_calling_enabled: bool = True,
) -> dict:
    """Create a fresh state dict for a new turn.

    Resets all fields to prevent checkpoint state leakage across turns.
    """
    state: dict[str, Any] = {
        # Input
        "user_query": user_input,
        "image_data": image_data,
        "extracted_entities": None,
        "image_findings": None,
        # Intent Classification
        "intent": None,
        "task_summary": None,
        "suggested_tool": None,
        # Tool Loop
        "current_tool": None,
        "current_args": None,
        "tool_results": [],
        "step_count": 0,
        "retry_count": 0,
        # Result Classification
        "last_result_classification": None,
        "last_result_summary": None,
        # Error Handling
        "error_messages": [],
        "clarification_request": None,
        # Internal (interrupt/approval)
        "_planned_tool": None,
        "_planned_args": None,
        # Session context (from frontend)
        "session_patient_id": patient_id,
        "tool_calling_enabled": tool_calling_enabled,
        "patient_context": None,
        # Output
        "final_response": None,
        "model_thinking": None,
    }
    if conversation_history:
        state["conversation_history"] = conversation_history
    return state


def _get_status_text(node_name: str, state_update: dict) -> str | None:
    """Return context-aware status text for the 7 v3 nodes."""
    state = state_update or {}

    if node_name == "input_assembly":
        return _pick("analyzing_query")

    if node_name == "intent_classify":
        intent = state.get("intent", "")
        if intent == "DIRECT":
            return _pick("composing_response")
        return _pick("selecting_tool")

    if node_name == "tool_select":
        planned_tool = state.get("_planned_tool")
        if planned_tool:
            return _pick_tool(planned_tool)
        return _pick("selecting_tool")

    if node_name == "tool_execute":
        return _pick("processing_results")

    if node_name == "result_classify":
        classification = state.get("last_result_classification", "")
        if classification.startswith("error"):
            return _pick("handling_error")
        return _pick("composing_response")

    if node_name == "error_handler":
        if state.get("_planned_tool"):
            return _pick("retrying")
        return _pick("composing_response")

    # synthesize — terminal, no next status
    return None


def _describe_tool_call(result: dict) -> str:
    """Generate a clinical-friendly description of a tool call."""
    tool = result.get("tool_name", "")
    args = result.get("args", result.get("arguments", {}))

    if tool == "check_drug_safety":
        drug = args.get("drug_name", "medication")
        return f"Checked safety profile for {drug}"
    if tool == "check_drug_interactions":
        drugs = args.get("drug_names", args.get("drugs", []))
        if isinstance(drugs, list):
            return f"Checked interactions: {', '.join(drugs)}"
        return "Checked drug interactions"
    if tool == "search_medical_literature":
        query = args.get("query", "")
        return f"Searched medical literature for: {query[:50]}"
    if tool == "find_clinical_trials":
        cond = args.get("condition", "")
        return f"Searched clinical trials for {cond[:50]}"
    if tool == "get_patient_chart":
        pid = args.get("patient_id", "")
        return f"Retrieved patient chart ({pid})"
    if tool == "search_patient":
        name = args.get("name", "")
        return f"Searched patient records for {name}"
    if tool == "add_allergy":
        substance = args.get("substance", "allergen")
        return f"Documented allergy to {substance}"
    if tool == "prescribe_medication":
        med = args.get("medication_name", "medication")
        return f"Prescribed {med}"
    if tool == "save_clinical_note":
        return "Saved clinical note"
    if tool == "analyze_medical_image":
        query = args.get("query", "")
        return f"Analyzed image: {query[:80]}" if query else "Analyzed attached image"
    return f"Consulted {TOOL_CLINICAL_LABELS.get(tool, tool.replace('_', ' '))}"


def _summarize_result(result: dict) -> str:
    """Generate a brief, content-rich summary of a tool result."""
    tool = result.get("tool_name", "")
    data = result.get("result", {})
    args = result.get("args", {})

    if tool == "check_drug_safety":
        warnings = data.get("boxed_warnings", [])
        if not warnings:
            return "No boxed warnings"
        first = warnings[0] if isinstance(warnings[0], str) else str(warnings[0])
        return f"{len(warnings)} warning(s): {first[:100]}..."

    if tool == "check_drug_interactions":
        interactions = data.get("interactions", [])
        if not interactions:
            return "No interactions found"
        ix = interactions[0]
        desc = ix.get("description", str(ix)) if isinstance(ix, dict) else str(ix)
        return f"{len(interactions)} interaction(s): {desc[:100]}..."

    if tool == "search_medical_literature":
        articles = data.get("articles", [])
        if not articles:
            return "No articles found"
        first = articles[0]
        title = first.get("title", str(first)) if isinstance(first, dict) else str(first)
        return f"{len(articles)} article(s) — {title[:100]}"

    if tool == "find_clinical_trials":
        trials = data.get("trials", [])
        if not trials:
            return "No trials found"
        first = trials[0]
        title = first.get("title", first.get("brief_title", str(first))) if isinstance(first, dict) else str(first)
        return f"{len(trials)} trial(s) — {title[:100]}"

    if tool == "search_patient":
        patients = data.get("patients", [])
        if not patients:
            return "No patients found"
        names = []
        for p in patients[:3]:
            names.append(p.get("name", p.get("full_name", "Unknown")) if isinstance(p, dict) else str(p))
        return ", ".join(names)

    if tool == "get_patient_chart":
        # Try to extract patient name from formatted result
        formatted = result.get("formatted_result", "")
        if formatted:
            first_line = formatted.split("\n")[0].strip()
            return first_line[:120] if first_line else "Chart loaded"
        return "Chart loaded"

    if tool == "add_allergy":
        substance = args.get("substance", "")
        reaction = args.get("reaction", "")
        parts = [p for p in [substance, reaction] if p]
        return f"Recorded: {', '.join(parts)}" if parts else "Allergy recorded"

    if tool == "prescribe_medication":
        med = args.get("medication_name", "")
        dosage = args.get("dosage", "")
        parts = [p for p in [med, dosage] if p]
        return f"Ordered: {' '.join(parts)}" if parts else "Prescription created"

    if tool == "save_clinical_note":
        note_type = args.get("note_type", "")
        return f"Saved {note_type} note" if note_type else "Note saved"

    if tool == "analyze_medical_image":
        findings = data.get("findings", "")
        if findings:
            clean = findings.replace("**", "").strip()
            lines = [l.strip() for l in clean.split("\n") if l.strip()]
            if lines and lines[0].lower().startswith("findings"):
                lines = lines[1:]
            preview = " ".join(lines[:2])
            return preview[:150] + "..." if len(preview) > 150 else preview
        return "No findings extracted"

    return "Done"


def _format_result_detail(result: dict) -> str | None:
    """Build a human-readable markdown string from a tool result."""
    tool = result.get("tool_name", "")
    data = result.get("result", {})

    if tool == "check_drug_safety":
        warnings = data.get("boxed_warnings", [])
        if not warnings:
            return "No boxed warnings found for this medication."
        lines = [f"**Boxed warnings ({len(warnings)}):**"]
        for w in warnings:
            text = w if isinstance(w, str) else str(w)
            lines.append(f"- {text}")
        return "\n".join(lines)

    if tool == "check_drug_interactions":
        interactions = data.get("interactions", [])
        if not interactions:
            return "No drug interactions detected."
        lines = [f"**Interactions ({len(interactions)}):**"]
        for ix in interactions:
            if isinstance(ix, dict):
                desc = ix.get("description", ix.get("name", str(ix)))
                severity = ix.get("severity", "")
                sev_tag = f" *({severity})*" if severity else ""
                lines.append(f"- {desc}{sev_tag}")
            else:
                lines.append(f"- {ix}")
        return "\n".join(lines)

    if tool == "search_medical_literature":
        articles = data.get("articles", [])
        if not articles:
            return "No relevant articles found."
        lines = [f"**Articles ({len(articles)}):**"]
        for a in articles[:5]:
            if isinstance(a, dict):
                title = a.get("title", "Untitled")
                year = a.get("year", a.get("pub_date", ""))
                lines.append(f"- {title}" + (f" ({year})" if year else ""))
            else:
                lines.append(f"- {a}")
        if len(articles) > 5:
            lines.append(f"- *...and {len(articles) - 5} more*")
        return "\n".join(lines)

    if tool == "find_clinical_trials":
        trials = data.get("trials", [])
        if not trials:
            return "No active clinical trials found."
        lines = [f"**Trials ({len(trials)}):**"]
        for t in trials[:5]:
            if isinstance(t, dict):
                title = t.get("title", t.get("brief_title", "Untitled"))
                status = t.get("status", t.get("overall_status", ""))
                lines.append(f"- {title}" + (f" — *{status}*" if status else ""))
            else:
                lines.append(f"- {t}")
        if len(trials) > 5:
            lines.append(f"- *...and {len(trials) - 5} more*")
        return "\n".join(lines)

    if tool == "get_patient_chart":
        # formatted_result has the chart summary
        formatted = result.get("formatted_result", "")
        return formatted if formatted else "Patient chart retrieved."

    if tool == "search_patient":
        patients = data.get("patients", [])
        if not patients:
            return "No patients found."
        lines = [f"**Patients ({len(patients)}):**"]
        for p in patients:
            if isinstance(p, dict):
                name = p.get("name", p.get("full_name", "Unknown"))
                pid = p.get("id", "")
                lines.append(f"- {name}" + (f" (`{pid}`)" if pid else ""))
            else:
                lines.append(f"- {p}")
        return "\n".join(lines)

    if tool == "analyze_medical_image":
        findings = data.get("findings", "")
        return findings if findings else "Image analysis completed."

    if tool in ("add_allergy", "prescribe_medication", "save_clinical_note"):
        formatted = result.get("formatted_result", "")
        return formatted if formatted else None

    # Generic fallback: use formatted_result
    formatted = result.get("formatted_result", "")
    return formatted if formatted else None


def _build_clinical_trace(
    state: dict, node_durations: dict[str, float]
) -> Any:
    """Build a clinical reasoning trace from the agent state."""
    from ..api.models.events import ClinicalTrace, TraceStep, TraceStepType

    steps: list[TraceStep] = []
    total_ms = 0.0

    # 1. Intent classification step
    intent = state.get("intent", "DIRECT")
    dur = node_durations.get("intent_classify", 0)
    total_ms += dur
    route_desc = "Direct answer" if intent == "DIRECT" else "Tool lookup"
    steps.append(
        TraceStep(
            type=TraceStepType.THOUGHT,
            label="Query Analysis",
            description=route_desc,
            duration_ms=dur,
        )
    )

    # 2. Model thinking (if captured from <unused94>...<unused95> block)
    thinking_text = state.get("model_thinking")
    if thinking_text:
        # Truncate for display label — full text in reasoning_text
        preview = thinking_text[:120] + "..." if len(thinking_text) > 120 else thinking_text
        steps.append(
            TraceStep(
                type=TraceStepType.THOUGHT,
                label="Model Reasoning",
                description=preview,
                reasoning_text=thinking_text,
            )
        )

    # 3. Successful tool calls
    for result in state.get("tool_results", []):
        if not result.get("success"):
            continue
        tool = result.get("tool_name", "unknown")
        dur = node_durations.get(f"tool_{tool}", node_durations.get("tool_execute", 0))
        total_ms += dur
        steps.append(
            TraceStep(
                type=TraceStepType.TOOL_CALL,
                label=TOOL_CLINICAL_LABELS.get(
                    tool, tool.replace("_", " ").title()
                ),
                description=_describe_tool_call(result),
                duration_ms=dur,
                tool_name=tool,
                tool_result_summary=_summarize_result(result),
                tool_result_detail=_format_result_detail(result),
                success=True,
            )
        )

    # 4. Synthesis step
    dur = node_durations.get("synthesize", 0)
    total_ms += dur
    steps.append(
        TraceStep(
            type=TraceStepType.SYNTHESIS,
            label="Composing Response",
            description="",
            duration_ms=dur,
        )
    )

    return ClinicalTrace(
        steps=steps,
        total_duration_ms=total_ms,
        tools_consulted=len(
            [s for s in steps if s.type == TraceStepType.TOOL_CALL]
        ),
    )


# =============================================================================
# Node labels (human-readable, for frontend display)
# =============================================================================

_NODE_LABELS = {
    "input_assembly": "Input Assembly",
    "intent_classify": "Intent Classification",
    "tool_select": "Tool Selection",
    "tool_execute": "Tool Execution",
    "result_classify": "Result Classification",
    "error_handler": "Error Handler",
    "synthesize": "Response Synthesis",
}


# =============================================================================
# Default GraphConfig instance (consumed by agent_runner.py)
# =============================================================================

GRAPH_CONFIG = GraphConfig(
    interrupt_before=["tool_execute"],
    extract_tool_proposal=_extract_tool_proposal,
    build_rejection_update=_build_rejection_update,
    terminal_nodes=frozenset({"synthesize"}),
    final_response_key="final_response",
    make_initial_state=_make_initial_state,
    get_status_text=_get_status_text,
    node_labels=_NODE_LABELS,
    build_clinical_trace=_build_clinical_trace,
)


# =============================================================================
# Graph builder
# =============================================================================


def build_graph(
    model: DocGemma,
    tool_executor: Callable | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: list[str] | None = None,
    stream_callback: StreamCallback = None,
) -> StateGraph:
    """Build the DocGemma v3 agent graph (7-node binary classification).

    Args:
        model: DocGemma model instance (must be loaded).
        tool_executor: Optional custom tool executor. If None, uses the
                       built-in tool registry. Signature: async (tool_name, args) -> dict.
        checkpointer: Optional checkpoint saver for persistence and interrupts.
                      Required if using interrupt_before.
        interrupt_before: List of node names to interrupt before execution.
        stream_callback: Callback for streaming token output.

    Returns:
        Compiled LangGraph workflow.
    """
    _executor = tool_executor if tool_executor is not None else registry_execute_tool

    workflow = StateGraph(AgentState)

    # === Add Nodes ===

    # 1. Input assembly (deterministic)
    workflow.add_node("input_assembly", input_assembly)

    # 2. Intent classify (LLM + Outlines)
    workflow.add_node(
        "intent_classify", lambda s: intent_classify(s, model)
    )

    # 3. Tool select (LLM + Outlines, two-stage)
    workflow.add_node("tool_select", lambda s: tool_select(s, model))

    # 4. Tool execute (async, deterministic)
    async def _tool_execute(s):
        return await tool_execute(s, _executor)

    workflow.add_node("tool_execute", _tool_execute)

    # 5. Result classify (LLM + Outlines)
    workflow.add_node(
        "result_classify", lambda s: result_classify(s, model)
    )

    # 5a. Error handler (hybrid: deterministic + LLM)
    workflow.add_node(
        "error_handler", lambda s: error_handler(s, model)
    )

    # 7. Synthesize (LLM streaming, terminal)
    async def _synthesize(s):
        return await synthesize(s, model, stream_callback)

    workflow.add_node("synthesize", _synthesize)

    # === Entry Point ===
    workflow.set_entry_point("input_assembly")

    # === Edges ===

    # input_assembly → intent_classify
    workflow.add_edge("input_assembly", "intent_classify")

    # intent_classify → conditional: DIRECT → synthesize, TOOL_NEEDED → tool_select
    workflow.add_conditional_edges(
        "intent_classify",
        route_after_intent,
        {"synthesize": "synthesize", "tool_select": "tool_select"},
    )

    # tool_select → tool_execute
    workflow.add_edge("tool_select", "tool_execute")

    # tool_execute → result_classify
    workflow.add_edge("tool_execute", "result_classify")

    # result_classify → conditional: synthesize / tool_select / error_handler
    workflow.add_conditional_edges(
        "result_classify",
        route_after_result_classify,
        {
            "synthesize": "synthesize",
            "tool_select": "tool_select",
            "error_handler": "error_handler",
        },
    )

    # error_handler → conditional: tool_execute (retry) / tool_select (different) / synthesize (skip)
    workflow.add_conditional_edges(
        "error_handler",
        route_after_error_handler,
        {
            "tool_execute": "tool_execute",
            "tool_select": "tool_select",
            "synthesize": "synthesize",
        },
    )

    # synthesize → END
    workflow.add_edge("synthesize", END)

    # === Compile ===
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before is not None:
        compile_kwargs["interrupt_before"] = interrupt_before

    return workflow.compile(**compile_kwargs)


# =============================================================================
# High-level agent interface
# =============================================================================


class DocGemmaAgent:
    """High-level agent interface wrapping the LangGraph workflow."""

    def __init__(self, model: DocGemma, tool_executor: Callable | None = None):
        self.model: DocGemma = model
        self.tool_executor = tool_executor
        self._graph = None

    @property
    def graph(self):
        """Lazily build the graph."""
        if self._graph is None:
            self._graph = build_graph(self.model, self.tool_executor)
        return self._graph

    async def run(
        self,
        user_input: str,
        image_data: bytes | None = None,
    ) -> str:
        """Run the agent on a single user input.

        Args:
            user_input: The user's query text.
            image_data: Optional raw image bytes for vision analysis.

        Returns:
            The agent's final response string.
        """
        logger.info("=" * 60)
        logger.info(
            f"[AGENT] Starting run: {user_input[:80]}"
            f"{'...' if len(user_input) > 80 else ''}"
        )
        logger.info("=" * 60)

        initial_state = _make_initial_state(user_input, image_data, None)
        result = await self.graph.ainvoke(initial_state)

        logger.info("=" * 60)
        logger.info("[AGENT] Run completed")
        logger.info("=" * 60)

        return result.get("final_response", "I was unable to generate a response.")
