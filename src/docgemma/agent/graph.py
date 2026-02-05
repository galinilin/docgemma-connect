"""LangGraph workflow definition for DocGemma agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from .nodes import (
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

# Graph node definitions for visualization
GRAPH_NODES = [
    {"id": "image_detection", "label": "Image Detection", "type": "code"},
    {"id": "complexity_router", "label": "Complexity Router", "type": "llm"},
    {"id": "direct_response", "label": "Direct Response", "type": "llm"},
    {"id": "thinking_mode", "label": "Thinking Mode", "type": "llm"},
    {"id": "decompose_intent", "label": "Decompose Intent", "type": "llm"},
    {"id": "plan_tool", "label": "Plan Tool", "type": "llm"},
    {"id": "execute_tool", "label": "Execute Tool", "type": "tool"},
    {"id": "check_result", "label": "Check Result", "type": "code"},
    {"id": "synthesize_response", "label": "Synthesize Response", "type": "llm"},
]

GRAPH_EDGES = [
    {"source": "image_detection", "target": "complexity_router", "label": None},
    {"source": "complexity_router", "target": "direct_response", "label": "direct"},
    {"source": "complexity_router", "target": "thinking_mode", "label": "complex"},
    {"source": "direct_response", "target": "__end__", "label": None},
    {"source": "thinking_mode", "target": "decompose_intent", "label": None},
    {"source": "decompose_intent", "target": "synthesize_response", "label": "needs_clarification"},
    {"source": "decompose_intent", "target": "plan_tool", "label": "has_subtasks"},
    {"source": "plan_tool", "target": "execute_tool", "label": None},
    {"source": "execute_tool", "target": "check_result", "label": None},
    {"source": "check_result", "target": "plan_tool", "label": "continue"},
    {"source": "check_result", "target": "synthesize_response", "label": "done"},
    {"source": "synthesize_response", "target": "__end__", "label": None},
]


def build_graph(
    model: DocGemma,
    tool_executor: Callable | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: list[str] | None = None,
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
    workflow.add_node("direct_response", lambda s: direct_response(s, model))
    workflow.add_node("thinking_mode", lambda s: thinking_mode(s, model))
    workflow.add_node("decompose_intent", lambda s: decompose_intent(s, model))
    workflow.add_node("plan_tool", lambda s: plan_tool(s, model))

    # Execute tool with the selected executor
    async def _execute(s):
        return await execute_tool(s, _executor)

    workflow.add_node("execute_tool", _execute)
    workflow.add_node("check_result", check_result)
    workflow.add_node("synthesize_response", lambda s: synthesize_response(s, model))

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
