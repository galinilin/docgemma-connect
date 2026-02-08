"""LangGraph workflow definition for DocGemma v2 agent.

18-node 4-way triage architecture:
  image_detection → clinical_context_assembler → triage_router
    → direct    → synthesize_response → END
    → lookup    → fast_tool_validate → [fast_fix_args] → fast_execute → fast_check → synthesize_response → END
    → reasoning → thinking_mode → extract_tool_needs → [reasoning_execute → reasoning_continuation] → synthesize_response → END
    → multi_step → decompose_intent → plan_tool → loop_validate → [loop_fix_args] → loop_execute → assess_result → ... → synthesize_response → END
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from .nodes import (
    MAX_FAST_RETRIES,
    StreamCallback,
    assess_result,
    clinical_context_assembler,
    decompose_intent,
    error_handler,
    extract_tool_needs,
    fast_check,
    fast_execute,
    fast_fix_args,
    fast_tool_validate,
    image_detection,
    loop_execute,
    loop_fix_args,
    loop_validate,
    plan_tool,
    reasoning_continuation,
    reasoning_execute,
    synthesize_response,
    thinking_mode,
    triage_router,
)
from .state import DocGemmaState
from ..tools.registry import execute_tool as registry_execute_tool

if TYPE_CHECKING:
    from ..model import DocGemma

logger = logging.getLogger(__name__)


# ── Clinical-friendly labels for tool names ──────────────────────────────────
TOOL_CLINICAL_LABELS = {
    "check_drug_safety": "FDA Safety Database",
    "check_drug_interactions": "Drug Interaction Check",
    "search_medical_literature": "Medical Literature (PubMed)",
    "find_clinical_trials": "Clinical Trials Registry",
    "search_patient": "Patient Records Search",
    "get_patient_chart": "Patient Chart Review",
    "add_allergy": "Allergy Documentation",
    "prescribe_medication": "Medication Prescription",
    "save_clinical_note": "Clinical Note",
    "analyze_medical_image": "Medical Image Analysis",
}

# Human-readable status labels for tool execution
TOOL_STATUS_LABELS = {
    "check_drug_safety": "Checking FDA safety database...",
    "check_drug_interactions": "Checking drug interactions...",
    "search_medical_literature": "Searching medical literature...",
    "find_clinical_trials": "Searching clinical trials...",
    "search_patient": "Searching patient records...",
    "get_patient_chart": "Retrieving patient chart...",
    "add_allergy": "Documenting allergy...",
    "prescribe_medication": "Processing prescription...",
    "save_clinical_note": "Saving clinical note...",
    "analyze_medical_image": "Analyzing medical image...",
}


# ── GraphConfig ──────────────────────────────────────────────────────────────

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

    # Factory: (user_input, image_data, conversation_history) -> initial state dict.
    make_initial_state: Callable[[str, bytes | None, list[dict] | None], dict]

    # (node_name, state_update) -> status text or None.
    get_status_text: Callable[[str, dict], str | None] | None

    # node_id -> human-readable label.
    node_labels: dict[str, str]

    # (full_state, node_durations) -> ClinicalTrace or None.
    build_clinical_trace: Callable[[dict, dict[str, float]], Any] | None


# ── Helpers for the default GRAPH_CONFIG ─────────────────────────────────────

# Tools that modify patient data — require explicit user approval
_WRITE_TOOLS = frozenset({
    "add_allergy",
    "prescribe_medication",
    "save_clinical_note",
})


def _extract_tool_proposal(state: dict) -> tuple[str | None, dict, str]:
    """Read the planned tool from interrupt state.

    Returns (None, {}, "") for no-op or read-only tools so the graph
    auto-resumes without user approval.  Only write operations (allergy,
    prescription, clinical note) surface a ToolApprovalRequest.
    """
    planned_tool = state.get("_planned_tool")
    planned_args = state.get("_planned_args", {})
    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    intent = ""
    if subtasks and idx < len(subtasks):
        intent = subtasks[idx].get("intent", "")
    # For reasoning/lookup paths, use the user_input as intent fallback
    if not intent:
        intent = state.get("user_input", "")
    if not planned_tool or planned_tool == "none":
        return (None, {}, "")
    # Read-only tools auto-approve (no user prompt)
    if planned_tool not in _WRITE_TOOLS:
        return (None, {}, "")
    return (planned_tool, planned_args, intent)


def _build_rejection_update(state: dict, reason: str | None) -> dict:
    """Build state update dict for a rejected tool."""
    return {
        "_planned_tool": None,
        "_planned_args": None,
        "last_result_status": "done",
        "tool_results": state.get("tool_results", []) + [
            {
                "tool_name": state.get("_planned_tool", "unknown"),
                "arguments": state.get("_planned_args", {}),
                "result": {"rejected": True, "reason": reason or "User rejected"},
                "success": False,
            }
        ],
    }


def _make_initial_state(
    user_input: str,
    image_data: bytes | None,
    conversation_history: list[dict] | None,
) -> dict:
    """Create a fresh state dict for a new turn."""
    state: dict[str, Any] = {
        "user_input": user_input,
        "image_data": image_data,
        "image_present": False,
        # Clinical context
        "clinical_context": None,
        # Triage
        "triage_route": None,
        "triage_tool": None,
        "triage_query": None,
        # Reasoning
        "reasoning": None,
        "reasoning_tool_needs": None,
        "reasoning_continuation": None,
        # Agentic loop
        "subtasks": [],
        "current_subtask_index": 0,
        "tool_results": [],
        "loop_iterations": 0,
        "tool_retries": 0,
        # Tool execution
        "_planned_tool": None,
        "_planned_args": None,
        # Validation
        "validation_error": None,
        # Error handling
        "error_strategy": None,
        # Control flags
        "last_result_status": None,
        "needs_user_input": False,
        "missing_info": None,
        # Output
        "final_response": None,
    }
    if conversation_history:
        state["conversation_history"] = conversation_history
    return state


def _get_status_text(node_name: str, state_update: dict) -> str | None:
    """Return status text describing what will run NEXT after this node."""
    state = state_update or {}

    if node_name == "image_detection":
        return "Assembling context..."

    if node_name == "clinical_context_assembler":
        return "Analyzing query..."

    if node_name == "triage_router":
        route = state.get("triage_route", "direct")
        if route == "direct":
            return "Composing response..."
        if route == "lookup":
            return "Quick lookup..."
        if route == "reasoning":
            return "Clinical reasoning..."
        return "Breaking down your question..."

    if node_name == "fast_tool_validate":
        if state.get("validation_error"):
            return "Fixing arguments..."
        planned_tool = state.get("_planned_tool")
        if planned_tool:
            return TOOL_STATUS_LABELS.get(
                planned_tool, f"Using {planned_tool.replace('_', ' ')}..."
            )
        return None

    if node_name == "fast_fix_args":
        planned_tool = state.get("_planned_tool")
        if planned_tool:
            return TOOL_STATUS_LABELS.get(
                planned_tool, f"Using {planned_tool.replace('_', ' ')}..."
            )
        return None

    if node_name in ("fast_execute", "reasoning_execute", "loop_execute"):
        return "Processing results..."

    if node_name == "fast_check":
        status = state.get("last_result_status", "done")
        if status == "error":
            return "Retrying..."
        return "Composing response..."

    if node_name == "thinking_mode":
        return "Analyzing tool needs..."

    if node_name == "extract_tool_needs":
        if state.get("reasoning_tool_needs"):
            tool = state["reasoning_tool_needs"].get("tool", "")
            return TOOL_STATUS_LABELS.get(
                tool, f"Using {tool.replace('_', ' ')}..."
            )
        return "Composing response..."

    if node_name == "reasoning_continuation":
        return "Composing response..."

    if node_name == "decompose_intent":
        if state.get("needs_user_input"):
            return "Composing response..."
        return "Planning approach..."

    if node_name == "plan_tool":
        planned_tool = state.get("_planned_tool")
        if planned_tool and planned_tool != "none":
            return TOOL_STATUS_LABELS.get(
                planned_tool,
                f"Using {planned_tool.replace('_', ' ')}...",
            )
        return None

    if node_name == "loop_validate":
        if state.get("validation_error"):
            return "Fixing arguments..."
        return None

    if node_name == "loop_fix_args":
        return None

    if node_name == "assess_result":
        status = state.get("last_result_status", "done")
        if status == "error":
            return "Handling error..."
        if status == "continue":
            return "Planning next step..."
        return "Composing response..."

    if node_name == "error_handler":
        strategy = state.get("error_strategy", "")
        if strategy == "retry_same":
            return "Retrying..."
        if strategy == "retry_reformulate":
            return "Trying different approach..."
        if strategy == "skip_subtask":
            return "Moving on..."
        return None

    # Terminal nodes — no next status
    return None


def _describe_tool_call(result: dict) -> str:
    """Generate a clinical-friendly description of a tool call."""
    tool = result.get("tool_name", "")
    args = result.get("arguments", {})

    if tool == "check_drug_safety":
        drug = args.get("drug_name", "medication")
        return f"Checked safety profile for {drug}"
    elif tool == "check_drug_interactions":
        drugs = args.get("drug_list", "")
        if drugs:
            return f"Checked interactions: {drugs}"
        return "Checked drug interactions"
    elif tool == "search_medical_literature":
        query = args.get("query", "")
        return f"Searched medical literature for: {query[:50]}..."
    elif tool == "find_clinical_trials":
        query = args.get("query", "")
        return f"Searched clinical trials for {query[:50]}"
    elif tool == "get_patient_chart":
        patient_id = args.get("patient_id", "")
        return f"Retrieved patient chart ({patient_id})"
    elif tool == "search_patient":
        name = args.get("name", "")
        return f"Searched patient records for {name}"
    elif tool == "add_allergy":
        substance = args.get("substance", "allergen")
        return f"Documented allergy to {substance}"
    elif tool == "prescribe_medication":
        med = args.get("medication_name", "medication")
        return f"Prescribed {med}"
    elif tool == "save_clinical_note":
        return "Saved clinical note"
    elif tool == "analyze_medical_image":
        return "Analyzed medical image"
    else:
        return f"Consulted {TOOL_CLINICAL_LABELS.get(tool, tool.replace('_', ' '))}"


def _summarize_result(result: dict) -> str:
    """Generate a brief summary of a tool result."""
    tool = result.get("tool_name", "")
    data = result.get("result", {})

    if tool == "check_drug_safety":
        warnings = data.get("boxed_warnings", [])
        if warnings:
            return f"Found {len(warnings)} boxed warning(s)"
        return "No boxed warnings found"
    elif tool == "check_drug_interactions":
        interactions = data.get("interactions", [])
        if interactions:
            return f"Found {len(interactions)} potential interaction(s)"
        return "No interactions found"
    elif tool == "search_medical_literature":
        articles = data.get("articles", [])
        return f"Found {len(articles)} relevant article(s)"
    elif tool == "find_clinical_trials":
        trials = data.get("trials", [])
        return f"Found {len(trials)} active trial(s)"
    elif tool == "search_patient":
        patients = data.get("patients", [])
        return f"Found {len(patients)} patient(s)"
    elif tool == "get_patient_chart":
        return "Chart retrieved"
    elif tool == "add_allergy":
        return "Allergy documented"
    elif tool == "prescribe_medication":
        return "Medication prescribed"
    elif tool == "save_clinical_note":
        return "Note saved"
    else:
        return "Completed successfully"


def _build_clinical_trace(
    state: dict, node_durations: dict[str, float]
) -> Any:
    """Build a clinical reasoning trace from the agent state."""
    from ..api.models.events import ClinicalTrace, TraceStep, TraceStepType

    steps: list[TraceStep] = []
    total_ms = 0.0

    # 1. Triage step
    route = state.get("triage_route", "direct")
    dur = node_durations.get("triage_router", 0)
    total_ms += dur
    route_labels = {
        "direct": "Direct Answer",
        "lookup": "Quick Lookup",
        "reasoning": "Clinical Reasoning",
        "multi_step": "Multi-Step Analysis",
    }
    steps.append(
        TraceStep(
            type=TraceStepType.THOUGHT,
            label="Triage",
            description=f"Classified as: {route_labels.get(route, route)}",
            duration_ms=dur,
        )
    )

    # 2. Reasoning step (if present)
    if state.get("reasoning"):
        dur = node_durations.get("thinking_mode", 0)
        total_ms += dur
        reasoning_text = state["reasoning"]
        if len(reasoning_text) > 500:
            reasoning_text = reasoning_text[:500] + "..."
        steps.append(
            TraceStep(
                type=TraceStepType.THOUGHT,
                label="Clinical Reasoning",
                description="Analyzed query to plan approach",
                duration_ms=dur,
                reasoning_text=reasoning_text,
            )
        )

    # 3. Reasoning continuation (if present)
    if state.get("reasoning_continuation"):
        dur = node_durations.get("reasoning_continuation", 0)
        total_ms += dur
        steps.append(
            TraceStep(
                type=TraceStepType.THOUGHT,
                label="Reasoning (continued)",
                description="Integrated tool findings into analysis",
                duration_ms=dur,
            )
        )

    # 4. Successful tool calls
    for result in state.get("tool_results", []):
        if not result.get("success"):
            continue
        tool = result.get("tool_name", "unknown")
        dur = node_durations.get(
            f"tool_{tool}",
            node_durations.get("fast_execute",
                node_durations.get("reasoning_execute",
                    node_durations.get("loop_execute", 0))),
        )
        total_ms += dur
        steps.append(
            TraceStep(
                type=TraceStepType.TOOL_CALL,
                label=TOOL_CLINICAL_LABELS.get(tool, tool.replace("_", " ").title()),
                description=_describe_tool_call(result),
                duration_ms=dur,
                tool_name=tool,
                tool_result_summary=_summarize_result(result),
                success=True,
            )
        )

    # 5. Synthesis step
    dur = node_durations.get("synthesize_response", 0)
    total_ms += dur
    steps.append(
        TraceStep(
            type=TraceStepType.SYNTHESIS,
            label="Response Synthesis",
            description="Combined findings into clinical response",
            duration_ms=dur,
        )
    )

    return ClinicalTrace(
        steps=steps,
        total_duration_ms=total_ms,
        tools_consulted=len([s for s in steps if s.type == TraceStepType.TOOL_CALL]),
    )


# ── Node labels ──────────────────────────────────────────────────────────────
_NODE_LABELS = {
    "image_detection": "Image Detection",
    "clinical_context_assembler": "Context Assembly",
    "triage_router": "Triage Router",
    "fast_tool_validate": "Validate (Lookup)",
    "fast_fix_args": "Fix Args (Lookup)",
    "fast_execute": "Execute (Lookup)",
    "fast_check": "Check (Lookup)",
    "thinking_mode": "Thinking Mode",
    "extract_tool_needs": "Extract Tool Needs",
    "reasoning_execute": "Execute (Reasoning)",
    "reasoning_continuation": "Reasoning Continuation",
    "decompose_intent": "Decompose Intent",
    "plan_tool": "Plan Tool",
    "loop_validate": "Validate (Loop)",
    "loop_fix_args": "Fix Args (Loop)",
    "loop_execute": "Execute (Loop)",
    "assess_result": "Assess Result",
    "error_handler": "Error Handler",
    "synthesize_response": "Synthesize Response",
}


# ── Default config for the v2 graph ──────────────────────────────────────────
GRAPH_CONFIG = GraphConfig(
    interrupt_before=["fast_execute", "reasoning_execute", "loop_execute"],
    extract_tool_proposal=_extract_tool_proposal,
    build_rejection_update=_build_rejection_update,
    terminal_nodes=frozenset({"synthesize_response"}),
    final_response_key="final_response",
    make_initial_state=_make_initial_state,
    get_status_text=_get_status_text,
    node_labels=_NODE_LABELS,
    build_clinical_trace=_build_clinical_trace,
)


# ── Graph builder ────────────────────────────────────────────────────────────

def build_graph(
    model: DocGemma,
    tool_executor: Callable | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: list[str] | None = None,
    stream_callback: StreamCallback = None,
) -> StateGraph:
    """Build the DocGemma v2 agent graph (18-node 4-way triage).

    Args:
        model: DocGemma model instance (must be loaded)
        tool_executor: Optional custom tool executor. If None, uses the
                       built-in tool registry. Signature: async (tool_name, args) -> dict
        checkpointer: Optional checkpoint saver for persistence and interrupts.
                      Required if using interrupt_before.
        interrupt_before: List of node names to interrupt before execution.
                          Useful for human-in-the-loop approval.
        stream_callback: Callback for streaming token output.

    Returns:
        Compiled LangGraph workflow
    """
    _executor = tool_executor if tool_executor is not None else registry_execute_tool

    workflow = StateGraph(DocGemmaState)

    # === Add Nodes ===

    # 1. Image detection (pure code)
    workflow.add_node("image_detection", image_detection)

    # 2. Clinical context assembler (pure code)
    workflow.add_node("clinical_context_assembler", clinical_context_assembler)

    # 3. Triage router (LLM)
    workflow.add_node("triage_router", lambda s: triage_router(s, model))

    # --- LOOKUP path ---
    # 4. Fast tool validate (pure code)
    workflow.add_node("fast_tool_validate", fast_tool_validate)

    # 5. Fast fix args (LLM)
    workflow.add_node("fast_fix_args", lambda s: fast_fix_args(s, model))

    # 6. Fast execute (async)
    async def _fast_execute(s):
        return await fast_execute(s, _executor)
    workflow.add_node("fast_execute", _fast_execute)

    # 7. Fast check (pure code)
    workflow.add_node("fast_check", fast_check)

    # --- REASONING path ---
    # 8. Thinking mode (LLM)
    workflow.add_node("thinking_mode", lambda s: thinking_mode(s, model))

    # 9. Extract tool needs (LLM)
    workflow.add_node("extract_tool_needs", lambda s: extract_tool_needs(s, model))

    # 10. Reasoning execute (async)
    async def _reasoning_execute(s):
        return await reasoning_execute(s, _executor)
    workflow.add_node("reasoning_execute", _reasoning_execute)

    # 11. Reasoning continuation (LLM streaming)
    async def _reasoning_continuation(s):
        return await reasoning_continuation(s, model, stream_callback)
    workflow.add_node("reasoning_continuation", _reasoning_continuation)

    # --- MULTI_STEP path ---
    # 12. Decompose intent (LLM)
    workflow.add_node("decompose_intent", lambda s: decompose_intent(s, model))

    # 13. Plan tool (LLM)
    workflow.add_node("plan_tool", lambda s: plan_tool(s, model))

    # 14. Loop validate (pure code)
    workflow.add_node("loop_validate", loop_validate)

    # 15. Loop fix args (LLM)
    workflow.add_node("loop_fix_args", lambda s: loop_fix_args(s, model))

    # 16. Loop execute (async)
    async def _loop_execute(s):
        return await loop_execute(s, _executor)
    workflow.add_node("loop_execute", _loop_execute)

    # 17. Assess result (pure code)
    workflow.add_node("assess_result", assess_result)

    # 18. Error handler (pure code)
    workflow.add_node("error_handler", error_handler)

    # 19. Synthesize response (LLM streaming, terminal)
    async def _synthesize_response(s):
        return await synthesize_response(s, model, stream_callback)
    workflow.add_node("synthesize_response", _synthesize_response)

    # === Entry Point ===
    workflow.set_entry_point("image_detection")

    # === Edges ===

    # image_detection → clinical_context_assembler → triage_router
    workflow.add_edge("image_detection", "clinical_context_assembler")
    workflow.add_edge("clinical_context_assembler", "triage_router")

    # --- Triage routing (4-way) ---
    def route_triage(state: DocGemmaState) -> str:
        route = state.get("triage_route", "direct")
        mapping = {
            "direct": "synthesize_response",
            "lookup": "fast_tool_validate",
            "reasoning": "thinking_mode",
            "multi_step": "decompose_intent",
        }
        target = mapping.get(route, "synthesize_response")
        logger.info(f"[ROUTE] triage_router -> {target} (route={route})")
        return target

    workflow.add_conditional_edges(
        "triage_router",
        route_triage,
        {
            "synthesize_response": "synthesize_response",
            "fast_tool_validate": "fast_tool_validate",
            "thinking_mode": "thinking_mode",
            "decompose_intent": "decompose_intent",
        },
    )

    # --- LOOKUP path edges ---
    def route_fast_validate(state: DocGemmaState) -> str:
        if state.get("validation_error"):
            logger.info("[ROUTE] fast_tool_validate -> fast_fix_args (validation error)")
            return "fast_fix_args"
        logger.info("[ROUTE] fast_tool_validate -> fast_execute (valid)")
        return "fast_execute"

    workflow.add_conditional_edges(
        "fast_tool_validate",
        route_fast_validate,
        {"fast_fix_args": "fast_fix_args", "fast_execute": "fast_execute"},
    )
    workflow.add_edge("fast_fix_args", "fast_execute")
    workflow.add_edge("fast_execute", "fast_check")

    def route_fast_check(state: DocGemmaState) -> str:
        status = state.get("last_result_status")
        if status == "done":
            logger.info("[ROUTE] fast_check -> synthesize_response (done)")
            return "synthesize_response"
        # error + retries remaining → retry
        retries = state.get("tool_retries", 0)
        if retries <= MAX_FAST_RETRIES:
            logger.info(f"[ROUTE] fast_check -> fast_execute (retry {retries})")
            return "fast_execute"
        logger.info("[ROUTE] fast_check -> synthesize_response (max retries)")
        return "synthesize_response"

    workflow.add_conditional_edges(
        "fast_check",
        route_fast_check,
        {"synthesize_response": "synthesize_response", "fast_execute": "fast_execute"},
    )

    # --- REASONING path edges ---
    workflow.add_edge("thinking_mode", "extract_tool_needs")

    def route_extract_tool_needs(state: DocGemmaState) -> str:
        tool_needs = state.get("reasoning_tool_needs")
        if tool_needs and tool_needs.get("tool"):
            logger.info(f"[ROUTE] extract_tool_needs -> reasoning_execute (tool={tool_needs['tool']})")
            return "reasoning_execute"
        logger.info("[ROUTE] extract_tool_needs -> synthesize_response (no tools needed)")
        return "synthesize_response"

    workflow.add_conditional_edges(
        "extract_tool_needs",
        route_extract_tool_needs,
        {"reasoning_execute": "reasoning_execute", "synthesize_response": "synthesize_response"},
    )
    workflow.add_edge("reasoning_execute", "reasoning_continuation")
    workflow.add_edge("reasoning_continuation", "synthesize_response")

    # --- MULTI_STEP path edges ---
    def route_decompose(state: DocGemmaState) -> str:
        if state.get("needs_user_input"):
            logger.info("[ROUTE] decompose_intent -> synthesize_response (needs clarification)")
            return "synthesize_response"
        subtasks = state.get("subtasks", [])
        logger.info(f"[ROUTE] decompose_intent -> plan_tool ({len(subtasks)} subtasks)")
        return "plan_tool"

    workflow.add_conditional_edges(
        "decompose_intent",
        route_decompose,
        {"synthesize_response": "synthesize_response", "plan_tool": "plan_tool"},
    )

    workflow.add_edge("plan_tool", "loop_validate")

    def route_loop_validate(state: DocGemmaState) -> str:
        if state.get("validation_error"):
            logger.info("[ROUTE] loop_validate -> loop_fix_args (validation error)")
            return "loop_fix_args"
        logger.info("[ROUTE] loop_validate -> loop_execute (valid)")
        return "loop_execute"

    workflow.add_conditional_edges(
        "loop_validate",
        route_loop_validate,
        {"loop_fix_args": "loop_fix_args", "loop_execute": "loop_execute"},
    )
    workflow.add_edge("loop_fix_args", "loop_execute")
    workflow.add_edge("loop_execute", "assess_result")

    def route_assess_result(state: DocGemmaState) -> str:
        status = state.get("last_result_status")
        if status == "error":
            logger.info("[ROUTE] assess_result -> error_handler")
            return "error_handler"
        if status == "continue":
            logger.info("[ROUTE] assess_result -> plan_tool (next subtask)")
            return "plan_tool"
        # "done" or "needs_user_input"
        logger.info(f"[ROUTE] assess_result -> synthesize_response (status={status})")
        return "synthesize_response"

    workflow.add_conditional_edges(
        "assess_result",
        route_assess_result,
        {
            "error_handler": "error_handler",
            "plan_tool": "plan_tool",
            "synthesize_response": "synthesize_response",
        },
    )

    def route_error_handler(state: DocGemmaState) -> str:
        strategy = state.get("error_strategy", "skip_subtask")
        if strategy == "retry_same":
            logger.info("[ROUTE] error_handler -> loop_execute (retry same)")
            return "loop_execute"
        if strategy == "retry_reformulate":
            logger.info("[ROUTE] error_handler -> plan_tool (reformulate)")
            return "plan_tool"
        # skip_subtask
        if state.get("last_result_status") == "done":
            logger.info("[ROUTE] error_handler -> synthesize_response (all subtasks exhausted)")
            return "synthesize_response"
        logger.info("[ROUTE] error_handler -> plan_tool (skip to next subtask)")
        return "plan_tool"

    workflow.add_conditional_edges(
        "error_handler",
        route_error_handler,
        {
            "loop_execute": "loop_execute",
            "plan_tool": "plan_tool",
            "synthesize_response": "synthesize_response",
        },
    )

    # --- Terminal ---
    workflow.add_edge("synthesize_response", END)

    # === Compile ===
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before is not None:
        compile_kwargs["interrupt_before"] = interrupt_before

    return workflow.compile(**compile_kwargs)


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
        logger.info("=" * 60)
        logger.info(f"[AGENT] Starting run: {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
        logger.info("=" * 60)

        initial_state = _make_initial_state(user_input, image_data, None)
        result = await self.graph.ainvoke(initial_state)

        logger.info("=" * 60)
        logger.info("[AGENT] Run completed")
        logger.info("=" * 60)

        return result.get("final_response", "I was unable to generate a response.")

    def run_sync(
        self,
        user_input: str,
        image_data: bytes | None = None,
    ) -> str:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run(user_input, image_data))

        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(self.run(user_input, image_data))
