"""LangGraph workflow definition for DocGemma agent."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from .nodes import (
    StreamCallback,
    check_result,
    complexity_router,
    decompose_intent,
    direct_response,
    execute_tool,
    image_detection,
    plan_tool,
    synthesize_response,
    thinking_mode,
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

def _extract_tool_proposal(state: dict) -> tuple[str | None, dict, str]:
    """Read the planned tool from interrupt state."""
    planned_tool = state.get("_planned_tool")
    planned_args = state.get("_planned_args", {})
    subtasks = state.get("subtasks", [])
    idx = state.get("current_subtask_index", 0)
    intent = ""
    if subtasks and idx < len(subtasks):
        intent = subtasks[idx].get("intent", "")
    if not planned_tool or planned_tool == "none":
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
        "subtasks": [],
        "current_subtask_index": 0,
        "tool_results": [],
        "loop_iterations": 0,
        "tool_retries": 0,
        # Explicitly clear turn outputs to prevent checkpoint leakage
        "final_response": None,
        "complexity": None,
        "reasoning": None,
        "_planned_tool": None,
        "_planned_args": None,
        "last_result_status": None,
        "needs_user_input": False,
        "missing_info": None,
    }
    if conversation_history:
        state["conversation_history"] = conversation_history
    return state


def _get_status_text(node_name: str, state_update: dict) -> str | None:
    """Return status text describing what will run NEXT after this node."""
    state = state_update or {}

    if node_name == "image_detection":
        return "Analyzing query..."

    if node_name == "complexity_router":
        if state.get("complexity") == "direct":
            return "Composing response..."
        return "Clinical reasoning..."

    if node_name == "thinking_mode":
        return "Breaking down your question..."

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

    if node_name == "execute_tool":
        return "Processing results..."

    if node_name == "check_result":
        status = state.get("last_result_status", "done")
        if status == "continue":
            return "Planning next step..."
        return "Composing response..."

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
        drugs = args.get("drug_names", [])
        if len(drugs) >= 2:
            return f"Checked interactions between {drugs[0]} and {drugs[1]}"
        return "Checked drug interactions"
    elif tool == "search_medical_literature":
        query = args.get("query", "")
        return f"Searched medical literature for: {query[:50]}..."
    elif tool == "find_clinical_trials":
        condition = args.get("condition", "")
        return f"Searched clinical trials for {condition}"
    elif tool == "get_patient_chart":
        patient_id = args.get("patient_id", "")
        return f"Retrieved patient chart ({patient_id})"
    elif tool == "search_patient":
        return "Searched patient records"
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
    else:
        return "Completed successfully"


def _build_clinical_trace(
    state: dict, node_durations: dict[str, float]
) -> Any:
    """Build a clinical reasoning trace from the agent state."""
    # Import here to avoid circular dependency at module level
    from ..api.models.events import ClinicalTrace, TraceStep, TraceStepType

    steps: list[TraceStep] = []
    total_ms = 0.0

    # 1. Reasoning step (if present)
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

    # 2. Successful tool calls only
    for result in state.get("tool_results", []):
        if not result.get("success"):
            continue
        tool = result.get("tool_name", "unknown")
        dur = node_durations.get(f"tool_{tool}", node_durations.get("execute_tool", 0))
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

    # 3. Synthesis step
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
    "complexity_router": "Complexity Router",
    "direct_response": "Direct Response",
    "thinking_mode": "Thinking Mode",
    "decompose_intent": "Decompose Intent",
    "plan_tool": "Plan Tool",
    "execute_tool": "Execute Tool",
    "check_result": "Check Result",
    "synthesize_response": "Synthesize Response",
}


# ── Default config for the current 9-node graph ─────────────────────────────
GRAPH_CONFIG = GraphConfig(
    interrupt_before=["execute_tool"],
    extract_tool_proposal=_extract_tool_proposal,
    build_rejection_update=_build_rejection_update,
    terminal_nodes=frozenset({"synthesize_response", "direct_response"}),
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
    """Build the DocGemma agent graph.

    Args:
        model: DocGemma model instance (must be loaded)
        tool_executor: Optional custom tool executor. If None, uses the
                       built-in tool registry. Signature: async (tool_name, args) -> dict
        checkpointer: Optional checkpoint saver for persistence and interrupts.
                      Required if using interrupt_before.
        interrupt_before: List of node names to interrupt before execution.
                          Useful for human-in-the-loop approval (e.g., ["execute_tool"]).

    Returns:
        Compiled LangGraph workflow
    """
    # Use registry executor if no custom one provided
    _executor = tool_executor if tool_executor is not None else registry_execute_tool

    workflow = StateGraph(DocGemmaState)

    # === Add Nodes ===
    workflow.add_node("image_detection", image_detection)
    workflow.add_node("complexity_router", lambda s: complexity_router(s, model))
    async def _direct_response(s):
        return await direct_response(s, model, stream_callback)

    workflow.add_node("direct_response", _direct_response)
    workflow.add_node("thinking_mode", lambda s: thinking_mode(s, model))
    workflow.add_node("decompose_intent", lambda s: decompose_intent(s, model))
    workflow.add_node("plan_tool", lambda s: plan_tool(s, model))

    # Execute tool with the selected executor
    async def _execute(s):
        return await execute_tool(s, _executor)

    workflow.add_node("execute_tool", _execute)
    workflow.add_node("check_result", check_result)
    async def _synthesize_response(s):
        return await synthesize_response(s, model, stream_callback)

    workflow.add_node("synthesize_response", _synthesize_response)

    # === Entry Point ===
    workflow.set_entry_point("image_detection")

    # === Edges ===
    workflow.add_edge("image_detection", "complexity_router")

    # Route based on complexity
    def route_complexity(state: DocGemmaState) -> str:
        complexity = state.get("complexity", "complex")
        if complexity == "direct":
            logger.info("[ROUTE] complexity_router -> direct_response (simple query)")
            return "direct_response"
        logger.info("[ROUTE] complexity_router -> thinking_mode (complex query)")
        return "thinking_mode"

    workflow.add_conditional_edges(
        "complexity_router",
        route_complexity,
        {"direct_response": "direct_response", "thinking_mode": "thinking_mode"},
    )

    # Direct response ends
    workflow.add_edge("direct_response", END)

    # Thinking mode leads to decompose intent
    workflow.add_edge("thinking_mode", "decompose_intent")

    # Decompose leads to planning (or synthesis if clarification needed)
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

    # === Agentic Loop ===
    workflow.add_edge("plan_tool", "execute_tool")
    workflow.add_edge("execute_tool", "check_result")

    # Route based on check result
    def route_result(state: DocGemmaState) -> str:
        status = state.get("last_result_status", "done")
        idx = state.get("current_subtask_index", 0)
        subtasks = state.get("subtasks", [])

        if status == "continue":
            logger.info(f"[ROUTE] check_result -> plan_tool (subtask {idx + 1}/{len(subtasks)})")
            return "plan_tool"
        if status == "needs_user_input":
            logger.info("[ROUTE] check_result -> synthesize_response (needs user input)")
            return "synthesize_response"
        # "done" or "error" after max retries
        logger.info(f"[ROUTE] check_result -> synthesize_response (status={status})")
        return "synthesize_response"

    workflow.add_conditional_edges(
        "check_result",
        route_result,
        {
            "plan_tool": "plan_tool",
            "synthesize_response": "synthesize_response",
        },
    )

    # Synthesis ends
    workflow.add_edge("synthesize_response", END)

    # Compile with optional checkpointer and interrupt support
    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before is not None:
        compile_kwargs["interrupt_before"] = interrupt_before

    return workflow.compile(**compile_kwargs)


class DocGemmaAgent:
    """High-level agent interface wrapping the LangGraph workflow."""

    def __init__(self, model: DocGemma, tool_executor: Callable | None = None):
        """Initialize the agent.

        Args:
            model: DocGemma model instance
            tool_executor: Async callable(tool_name, args) -> result dict
        """
        self.model: DocGemma = model
        self.tool_executor = tool_executor
        self._graph = None

    @property
    def graph(self):
        """Lazily build the graph."""
        if self._graph is None:
            if not self.model.is_loaded:
                raise RuntimeError("Model must be loaded before using agent")
            self._graph = build_graph(self.model, self.tool_executor)
        return self._graph

    async def run(
        self,
        user_input: str,
        image_data: bytes | None = None,
    ) -> str:
        """Run the agent on a user query.

        Args:
            user_input: The user's query text
            image_data: Optional image bytes

        Returns:
            The agent's response string
        """
        logger.info("=" * 60)
        logger.info(f"[AGENT] Starting run: {user_input[:80]}{'...' if len(user_input) > 80 else ''}")
        logger.info("=" * 60)

        initial_state: DocGemmaState = {
            "user_input": user_input,
            "image_data": image_data,
            "image_present": False,
            "subtasks": [],
            "current_subtask_index": 0,
            "tool_results": [],
            "loop_iterations": 0,
            "tool_retries": 0,
        }

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
        """Synchronous wrapper for run().

        Works in both regular Python and Jupyter/Colab environments.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, use asyncio.run()
            return asyncio.run(self.run(user_input, image_data))

        # Already in an event loop (Jupyter/Colab) - use nest_asyncio
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(self.run(user_input, image_data))
