from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    emergency_check,
    complexity_router,
    persona_router,
    tool_node,
    synthesis_node,
)


def create_graph():
    """
    Creates the LangGraph agent.
    """
    graph = StateGraph(AgentState)

    graph.add_node("emergency_check", emergency_check)
    graph.add_node("persona_router", persona_router)
    graph.add_node("complexity_router", complexity_router)
    graph.add_node("tool_node", tool_node)
    graph.add_node("synthesis_node", synthesis_node)

    graph.set_entry_point("emergency_check")

    graph.add_conditional_edges(
        "emergency_check",
        lambda x: "synthesis_node" if x["is_emergency"] else "persona_router",
    )
    graph.add_edge("persona_router", "complexity_router")
    graph.add_conditional_edges(
        "complexity_router",
        lambda x: "synthesis_node" if not x["is_complex"] else "tool_node",
    )
    graph.add_edge("tool_node", "synthesis_node")
    graph.add_edge("synthesis_node", END)

    return graph.compile()
