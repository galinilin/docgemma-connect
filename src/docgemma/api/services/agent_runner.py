"""Agent runner service with interrupt support for human-in-the-loop."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.memory import MemorySaver

from ..models.events import (
    AgentEvent,
    ClinicalTrace,
    CompletionEvent,
    ErrorEvent,
    NodeEndEvent,
    NodeStartEvent,
    ToolApprovalRequestEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TraceStep,
    TraceStepType,
)
from ..models.session import Session, SessionStatus
from ...agent.graph import GRAPH_EDGES, GRAPH_NODES, build_graph
from ...agent.state import DocGemmaState
from ...tools.registry import execute_tool as registry_execute_tool

if TYPE_CHECKING:
    from ...model import DocGemma

logger = logging.getLogger(__name__)

# Clinical-friendly labels for tool names
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


class AgentRunner:
    """Runs the DocGemma agent with interrupt support for tool approval.

    This wraps the LangGraph workflow to provide:
    - Interrupt before tool execution for human approval
    - Event streaming for real-time UI updates
    - Resume capability after approval/rejection
    """

    def __init__(
        self,
        model: DocGemma,
        enable_tool_approval: bool = True,
    ):
        """Initialize the agent runner.

        Args:
            model: DocGemma model instance (must be loaded)
            enable_tool_approval: Whether to interrupt before tool execution
        """
        self.model = model
        self.enable_tool_approval = enable_tool_approval
        self._checkpointer = MemorySaver()

        # Build graph with interrupt support if tool approval enabled
        interrupt_before = ["execute_tool"] if enable_tool_approval else None
        self._graph = build_graph(
            model=model,
            tool_executor=registry_execute_tool,
            checkpointer=self._checkpointer,
            interrupt_before=interrupt_before,
        )

    def _make_thread_id(self, session_id: str) -> dict[str, str]:
        """Create a thread config for LangGraph."""
        return {"configurable": {"thread_id": session_id}}

    async def start_turn(
        self,
        session: Session,
        user_input: str,
        image_data: bytes | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Start a new turn in the conversation.

        Yields events until completion or interrupt (tool approval needed).

        Args:
            session: The session object
            user_input: User's message
            image_data: Optional image bytes
            conversation_history: Previous messages for context

        Yields:
            AgentEvent objects representing execution progress
        """
        session.status = SessionStatus.PROCESSING
        session.reset_for_new_turn()

        # Reset ALL state for new turn - critical to avoid stale data from checkpoint
        initial_state: DocGemmaState = {
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

        # Add conversation history if provided
        if conversation_history:
            initial_state["conversation_history"] = conversation_history

        config = self._make_thread_id(session.session_id)

        try:
            async for event in self._stream_execution(
                session, initial_state, config, is_resume=False
            ):
                yield event
        except Exception as e:
            logger.exception(f"Error in agent execution: {e}")
            yield ErrorEvent(
                error_type="execution_error",
                message=str(e),
                recoverable=False,
            )
            session.status = SessionStatus.ERROR

    async def resume_with_approval(
        self,
        session: Session,
        approved: bool,
        rejection_reason: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Resume execution after tool approval/rejection.

        Args:
            session: The session object (must have pending_approval)
            approved: Whether the tool was approved
            rejection_reason: Optional reason if rejected

        Yields:
            AgentEvent objects for remaining execution
        """
        if not session.pending_approval:
            yield ErrorEvent(
                error_type="invalid_state",
                message="No pending tool approval to respond to",
                recoverable=True,
            )
            return

        session.clear_pending_approval()
        session.status = SessionStatus.PROCESSING
        config = self._make_thread_id(session.session_id)

        if approved:
            # Continue execution - tool will be executed
            try:
                async for event in self._stream_execution(
                    session, None, config, is_resume=True
                ):
                    yield event
            except Exception as e:
                logger.exception(f"Error resuming execution: {e}")
                yield ErrorEvent(
                    error_type="execution_error",
                    message=str(e),
                    recoverable=False,
                )
                session.status = SessionStatus.ERROR
        else:
            # Tool rejected - update state and skip to synthesis
            yield NodeStartEvent(
                node_id="synthesize_response",
                node_label="Synthesize Response",
            )

            # Get current state and modify it to skip tool execution
            state = self._graph.get_state(config)
            if state and state.values:
                # Mark tool as rejected and jump to synthesis
                updated_state = {
                    **state.values,
                    "_planned_tool": None,
                    "_planned_args": None,
                    "last_result_status": "done",
                    "tool_results": state.values.get("tool_results", []) + [
                        {
                            "tool_name": session.pending_approval.tool_name if session.pending_approval else "unknown",
                            "arguments": session.pending_approval.tool_args if session.pending_approval else {},
                            "result": {"rejected": True, "reason": rejection_reason or "User rejected"},
                            "success": False,
                        }
                    ],
                }

                # Update the state
                self._graph.update_state(config, updated_state)

                # Resume execution
                try:
                    async for event in self._stream_execution(
                        session, None, config, is_resume=True
                    ):
                        yield event
                except Exception as e:
                    logger.exception(f"Error after rejection: {e}")
                    yield ErrorEvent(
                        error_type="execution_error",
                        message=str(e),
                        recoverable=False,
                    )
                    session.status = SessionStatus.ERROR

    async def _stream_execution(
        self,
        session: Session,
        initial_state: DocGemmaState | None,
        config: dict,
        is_resume: bool = False,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream execution events from the graph.

        Args:
            session: Session object to update
            initial_state: Initial state (None if resuming)
            config: LangGraph config with thread_id
            is_resume: Whether this is resuming after interrupt

        Yields:
            AgentEvent objects
        """
        node_start_times: dict[str, float] = {}
        node_durations: dict[str, float] = {}
        completion_emitted = False  # Guard against multiple completions

        # Terminal nodes that produce final_response
        terminal_nodes = {"synthesize_response", "direct_response"}

        input_data = initial_state if not is_resume else None

        async for event in self._graph.astream(
            input_data, config=config, stream_mode="updates"
        ):
            # event is a dict like {node_name: state_update}
            for node_name, state_update in event.items():
                if node_name == "__interrupt__":
                    # Interrupted before execute_tool - need approval
                    current_state = self._graph.get_state(config)
                    if current_state and current_state.values:
                        planned_tool = current_state.values.get("_planned_tool")
                        planned_args = current_state.values.get("_planned_args", {})
                        subtasks = current_state.values.get("subtasks", [])
                        idx = current_state.values.get("current_subtask_index", 0)

                        intent = ""
                        if subtasks and idx < len(subtasks):
                            intent = subtasks[idx].get("intent", "")

                        if planned_tool and planned_tool != "none":
                            session.set_pending_approval(
                                tool_name=planned_tool,
                                tool_args=planned_args,
                                subtask_intent=intent,
                                checkpoint_id=str(current_state.config.get("configurable", {}).get("checkpoint_id", "")),
                            )

                            yield ToolApprovalRequestEvent(
                                tool_name=planned_tool,
                                tool_args=planned_args,
                                subtask_intent=intent,
                            )
                            return  # Stop streaming, wait for approval
                    continue

                # Regular node execution
                start_time = node_start_times.get(node_name)
                if start_time is None:
                    # Node starting
                    node_start_times[node_name] = time.perf_counter()
                    node_label = self._get_node_label(node_name)
                    session.current_node = node_name

                    yield NodeStartEvent(node_id=node_name, node_label=node_label)

                # Node completed
                elapsed_ms = (time.perf_counter() - node_start_times.get(node_name, time.perf_counter())) * 1000
                node_label = self._get_node_label(node_name)
                node_durations[node_name] = elapsed_ms

                if node_name not in session.completed_nodes:
                    session.completed_nodes.append(node_name)

                yield NodeEndEvent(
                    node_id=node_name,
                    node_label=node_label,
                    duration_ms=elapsed_ms,
                )

                # Check if this is a tool execution node
                if node_name == "execute_tool" and state_update:
                    tool_results = state_update.get("tool_results", [])
                    if tool_results:
                        last_result = tool_results[-1]
                        yield ToolExecutionEndEvent(
                            tool_name=last_result.get("tool_name", "unknown"),
                            success=last_result.get("success", False),
                            result=last_result.get("result", {}),
                            duration_ms=elapsed_ms,
                        )

                # Only emit completion from terminal nodes and only once
                if (
                    not completion_emitted
                    and node_name in terminal_nodes
                    and state_update
                    and state_update.get("final_response")
                ):
                    final_response = state_update["final_response"]
                    completion_emitted = True

                    # Get tool call count and build trace from state
                    full_state = self._graph.get_state(config)
                    tool_count = 0
                    clinical_trace = None
                    if full_state and full_state.values:
                        tool_count = len(full_state.values.get("tool_results", []))
                        clinical_trace = self._build_clinical_trace(
                            full_state.values, node_durations
                        )

                    session.status = SessionStatus.ACTIVE
                    yield CompletionEvent(
                        final_response=final_response,
                        tool_calls_made=tool_count,
                        clinical_trace=clinical_trace,
                    )

    def _get_node_label(self, node_id: str) -> str:
        """Get human-readable label for a node."""
        for node in GRAPH_NODES:
            if node["id"] == node_id:
                return node["label"]
        return node_id.replace("_", " ").title()

    def _describe_tool_call(self, result: dict) -> str:
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

    def _summarize_result(self, result: dict) -> str:
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
        self, state: dict, node_durations: dict[str, float]
    ) -> ClinicalTrace:
        """Build a clinical reasoning trace from the agent state."""
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
                    description=self._describe_tool_call(result),
                    duration_ms=dur,
                    tool_name=tool,
                    tool_result_summary=self._summarize_result(result),
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

    def get_graph_visualization(self, session: Session) -> dict[str, Any]:
        """Get graph state for visualization.

        Args:
            session: The session to get state for

        Returns:
            Dict with nodes, edges, current_node, subtasks, tool_results
        """
        config = self._make_thread_id(session.session_id)
        state = self._graph.get_state(config)

        # Build nodes with status
        nodes = []
        for node_def in GRAPH_NODES:
            status = "pending"
            if node_def["id"] in session.completed_nodes:
                status = "completed"
            elif node_def["id"] == session.current_node:
                status = "active"

            nodes.append({
                "id": node_def["id"],
                "label": node_def["label"],
                "status": status,
                "node_type": node_def["type"],
            })

        # Build edges with active state
        edges = []
        for edge_def in GRAPH_EDGES:
            # An edge is active if its source is completed and target is current or completed
            active = (
                edge_def["source"] in session.completed_nodes
                and (
                    edge_def["target"] == session.current_node
                    or edge_def["target"] in session.completed_nodes
                )
            )
            edges.append({
                "source": edge_def["source"],
                "target": edge_def["target"],
                "label": edge_def["label"],
                "active": active,
            })

        # Get subtasks and tool results from state
        subtasks = []
        tool_results = []
        if state and state.values:
            subtasks = state.values.get("subtasks", [])
            tool_results = state.values.get("tool_results", [])

        return {
            "nodes": nodes,
            "edges": edges,
            "current_node": session.current_node,
            "subtasks": subtasks,
            "tool_results": tool_results,
        }
