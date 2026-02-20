"""Agent runner service with interrupt support for human-in-the-loop."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.memory import MemorySaver

import httpx

from ..models.events import (
    AgentEvent,
    AgentStatusEvent,
    CompletionEvent,
    ErrorEvent,
    NodeEndEvent,
    NodeStartEvent,
    StreamingTextEvent,
    ToolApprovalRequestEvent,
    ToolExecutionEndEvent,
)
from ..models.session import Session, SessionStatus
from ...agent.graph import GRAPH_CONFIG, GraphConfig, build_graph
from ...tools.registry import execute_tool as registry_execute_tool

if TYPE_CHECKING:
    from ...model import DocGemma

logger = logging.getLogger(__name__)

_ENDPOINT_DOWN_RESPONSE = (
    "I'm sorry, I'm temporarily unable to process your request. Please try again in a few moments."
)


def _is_endpoint_error(exc: Exception) -> bool:
    """Check if an exception indicates the model endpoint is unreachable."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (404, 502, 503, 504)
    if isinstance(exc, (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException)):
        return True
    # Check wrapped cause
    cause = exc.__cause__ or exc.__context__
    if cause and cause is not exc:
        return _is_endpoint_error(cause)
    return False


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
        graph_config: GraphConfig | None = None,
        enable_tool_approval: bool = True,
    ):
        """Initialize the agent runner.

        Args:
            model: DocGemma model instance (must be loaded)
            graph_config: Graph topology configuration. Defaults to GRAPH_CONFIG.
            enable_tool_approval: Whether to interrupt before tool execution
        """
        self.model = model
        self._cfg = graph_config or GRAPH_CONFIG
        self.enable_tool_approval = enable_tool_approval
        self._checkpointer = MemorySaver()
        self._interrupt_before = self._cfg.interrupt_before if enable_tool_approval else None

        # Build default graph (no streaming callback) for resume operations
        self._graph = build_graph(
            model=model,
            tool_executor=registry_execute_tool,
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
        )

    def _build_graph_with_callback(self, stream_callback=None):
        """Build a graph with optional streaming callback."""
        return build_graph(
            model=self.model,
            tool_executor=registry_execute_tool,
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
            stream_callback=stream_callback,
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
        patient_id: str | None = None,
        tool_calling_enabled: bool = True,
        thinking_enabled: bool = False,
        previous_image_findings: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Start a new turn in the conversation.

        Yields events until completion or interrupt (tool approval needed).

        Args:
            session: The session object
            user_input: User's message
            image_data: Optional image bytes
            conversation_history: Previous messages for context
            patient_id: Optional patient ID from frontend selector
            tool_calling_enabled: Whether the agent should use tools
            thinking_enabled: Whether to run preliminary thinking step
            previous_image_findings: Image findings from a prior turn

        Yields:
            AgentEvent objects representing execution progress
        """
        session.status = SessionStatus.PROCESSING
        session.reset_for_new_turn()

        initial_state = self._cfg.make_initial_state(
            user_input, image_data, conversation_history,
            patient_id=patient_id,
            tool_calling_enabled=tool_calling_enabled,
            thinking_enabled=thinking_enabled,
            previous_image_findings=previous_image_findings,
        )

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
        edited_args: dict | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Resume execution after tool approval/rejection.

        Args:
            session: The session object (must have pending_approval)
            approved: Whether the tool was approved
            rejection_reason: Optional reason if rejected
            edited_args: Optional user-edited tool arguments to replace _planned_args

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
            # Apply user's edited args to graph state before resuming
            if edited_args:
                self._graph.update_state(config, {"_planned_args": edited_args})

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
            # Tool rejected - update state and resume; graph routing decides next node
            state = self._graph.get_state(config)
            if state and state.values:
                rejection_update = self._cfg.build_rejection_update(
                    state.values, rejection_reason
                )
                self._graph.update_state(config, rejection_update)

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
        initial_state: dict | None,
        config: dict,
        is_resume: bool = False,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream execution events from the graph.

        Uses an asyncio.Queue bridge so that token-level streaming events
        emitted during node execution (via stream_callback) can be yielded
        to the caller before the node completes.

        Args:
            session: Session object to update
            initial_state: Initial state (None if resuming)
            config: LangGraph config with thread_id
            is_resume: Whether this is resuming after interrupt

        Yields:
            AgentEvent objects
        """
        node_durations: dict[str, float] = {}
        # Track when the last node update arrived; the delta gives us the
        # execution time of the current node (stream_mode="updates" emits
        # after each node completes, so the wall-clock gap ≈ node duration).
        last_node_time: float = time.perf_counter()
        completion_emitted = False

        input_data = initial_state if not is_resume else None

        # Emit an initial status event immediately so the user sees feedback
        # before the first node completes (input_assembly may be slow when
        # it runs image analysis).
        if input_data and not is_resume:
            has_image = input_data.get("image_data") is not None
            initial_status = "Analyzing medical image..." if has_image else "Processing your question..."
            yield AgentStatusEvent(
                status_text=initial_status,
                node_id="input_assembly",
            )

        # Queue bridge: streaming tokens and graph updates flow through here
        event_queue: asyncio.Queue[AgentEvent | dict | None] = asyncio.Queue()

        # Track which node is currently streaming so the frontend can route
        # tokens to the correct UI component (thinking section vs response).
        streaming_ctx = {
            "node_id": "preliminary_thinking"
            if (input_data and input_data.get("thinking_enabled"))
            else "terminal"
        }

        async def _stream_callback(text: str) -> None:
            """Push streaming text tokens into the queue."""
            await event_queue.put(
                StreamingTextEvent(text=text, node_id=streaming_ctx["node_id"])
            )

        # Build graph with streaming callback for this execution
        graph = self._build_graph_with_callback(stream_callback=_stream_callback)
        # Update default graph reference so get_state works
        self._graph = graph

        async def _run_graph() -> None:
            """Run graph iteration and push updates to queue.

            Automatically resumes the graph when it interrupts before
            a node with a no-op tool (planned_tool is None or "none").
            """
            try:
                data = input_data
                while True:
                    async for event in graph.astream(
                        data, config=config, stream_mode="updates"
                    ):
                        await event_queue.put(event)

                    # Check if graph paused at an interrupt
                    current_state = graph.get_state(config)
                    if current_state and current_state.next:
                        # Graph is paused — check if it's a no-op tool
                        tool_name, _, _ = self._cfg.extract_tool_proposal(
                            current_state.values or {}
                        )
                        if not tool_name:
                            # Auto-resume: skip the interrupt
                            data = None
                            continue
                    # Graph finished or paused for real tool approval
                    break
            except Exception as e:
                if _is_endpoint_error(e):
                    logger.warning(f"Model endpoint unavailable: {e}")
                    await event_queue.put(
                        CompletionEvent(
                            final_response=_ENDPOINT_DOWN_RESPONSE,
                            tool_calls_made=0,
                            clinical_trace=None,
                        )
                    )
                else:
                    await event_queue.put(
                        ErrorEvent(
                            error_type="execution_error",
                            message=str(e),
                            recoverable=False,
                        )
                    )
            finally:
                await event_queue.put(None)  # Sentinel

        graph_task = asyncio.create_task(_run_graph())

        try:
            while True:
                item = await event_queue.get()

                # Sentinel: graph is done
                if item is None:
                    break

                # StreamingTextEvent from callback — yield directly
                if isinstance(item, StreamingTextEvent):
                    yield item
                    continue

                # ErrorEvent from graph task exception
                if isinstance(item, ErrorEvent):
                    yield item
                    continue

                # CompletionEvent from graph task (e.g. endpoint-down fallback)
                if isinstance(item, CompletionEvent):
                    completion_emitted = True
                    session.status = SessionStatus.ACTIVE
                    yield item
                    continue

                # Regular graph update dict: {node_name: state_update}
                event = item
                for node_name, state_update in event.items():
                    if node_name == "__interrupt__":
                        current_state = graph.get_state(config)
                        if current_state and current_state.values:
                            tool_name, tool_args, intent = self._cfg.extract_tool_proposal(
                                current_state.values
                            )

                            if tool_name:
                                session.set_pending_approval(
                                    tool_name=tool_name,
                                    tool_args=tool_args,
                                    subtask_intent=intent,
                                    checkpoint_id=str(current_state.config.get("configurable", {}).get("checkpoint_id", "")),
                                )

                                yield ToolApprovalRequestEvent(
                                    tool_name=tool_name,
                                    tool_args=tool_args,
                                    subtask_intent=intent,
                                )
                                return

                            # No-op tool: _run_graph() will auto-resume.
                            # Emit status so user sees progress.
                            yield AgentStatusEvent(
                                status_text="Composing response...",
                                node_id="plan_tool",
                            )
                        continue

                    # Reset streaming context after thinking node completes
                    # so subsequent streaming (synthesis) uses "terminal".
                    if node_name == "preliminary_thinking":
                        streaming_ctx["node_id"] = "terminal"

                    # Regular node execution — measure wall-clock since last update
                    now = time.perf_counter()
                    elapsed_ms = (now - last_node_time) * 1000
                    last_node_time = now
                    node_durations[node_name] = elapsed_ms

                    node_label = self._cfg.node_labels.get(
                        node_name, node_name.replace("_", " ").title()
                    )

                    yield NodeStartEvent(node_id=node_name, node_label=node_label)
                    yield NodeEndEvent(
                        node_id=node_name,
                        node_label=node_label,
                        duration_ms=elapsed_ms,
                    )

                    # Emit forward-looking status: what's running NEXT
                    if self._cfg.get_status_text:
                        next_status = self._cfg.get_status_text(
                            node_name, state_update
                        )
                        if next_status:
                            yield AgentStatusEvent(
                                status_text=next_status,
                                node_id=node_name,
                            )

                    # Emit tool execution end for any node producing tool_results
                    if state_update:
                        tool_results = state_update.get("tool_results", [])
                        if tool_results:
                            last_result = tool_results[-1]
                            yield ToolExecutionEndEvent(
                                tool_name=last_result.get("tool_name", "unknown"),
                                success=last_result.get("success", False),
                                result=last_result.get("result", {}),
                                duration_ms=elapsed_ms,
                            )

                    if (
                        not completion_emitted
                        and node_name in self._cfg.terminal_nodes
                        and state_update
                        and state_update.get(self._cfg.final_response_key)
                    ):
                        final_response = state_update[self._cfg.final_response_key]
                        completion_emitted = True

                        full_state = graph.get_state(config)
                        tool_count = 0
                        clinical_trace = None
                        if full_state and full_state.values:
                            tool_count = len(full_state.values.get("tool_results", []))
                            if self._cfg.build_clinical_trace:
                                clinical_trace = self._cfg.build_clinical_trace(
                                    full_state.values, node_durations
                                )

                        preliminary_thinking_text = None
                        image_findings_text = None
                        if full_state and full_state.values:
                            preliminary_thinking_text = full_state.values.get("preliminary_thinking_text")
                            image_findings_text = full_state.values.get("image_findings")

                        session.status = SessionStatus.ACTIVE
                        yield CompletionEvent(
                            final_response=final_response,
                            tool_calls_made=tool_count,
                            clinical_trace=clinical_trace,
                            preliminary_thinking=preliminary_thinking_text,
                            image_findings=image_findings_text,
                        )
        finally:
            if not graph_task.done():
                graph_task.cancel()
                try:
                    await graph_task
                except asyncio.CancelledError:
                    pass
