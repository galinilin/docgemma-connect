"""LangGraph workflow definition for DocGemma agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

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

if TYPE_CHECKING:
    from ..protocols import DocGemmaProtocol

logger = logging.getLogger(__name__)


def build_graph(model: DocGemmaProtocol, tool_executor: Callable | None = None) -> StateGraph:
    """Build the DocGemma agent graph.

    Args:
        model: DocGemma model instance (must be loaded)
        tool_executor: Async callable(tool_name, args) -> result dict.
                       If None, tools will be skipped.

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(DocGemmaState)

    # === Add Nodes ===
    workflow.add_node("image_detection", image_detection)
    workflow.add_node("complexity_router", lambda s: complexity_router(s, model))
    workflow.add_node("direct_response", lambda s: direct_response(s, model))
    workflow.add_node("thinking_mode", lambda s: thinking_mode(s, model))
    workflow.add_node("decompose_intent", lambda s: decompose_intent(s, model))
    workflow.add_node("plan_tool", lambda s: plan_tool(s, model))

    # Execute tool needs async handling
    async def _execute(s):
        if tool_executor is None:
            # No executor, skip tool execution
            return {**s, "last_result_status": "success", "_planned_tool": None}
        return await execute_tool(s, tool_executor)

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

    return workflow.compile()


class DocGemmaAgent:
    """High-level agent interface wrapping the LangGraph workflow."""

    def __init__(self, model: DocGemmaProtocol, tool_executor: Callable | None = None):
        """Initialize the agent.

        Args:
            model: DocGemma-compatible model (DocGemma or RemoteDocGemma)
            tool_executor: Async callable(tool_name, args) -> result dict
        """
        self.model: DocGemmaProtocol = model
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
