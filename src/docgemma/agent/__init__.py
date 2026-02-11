"""DocGemma Agent - LangGraph-based medical AI assistant (v3: 7-node binary classification)."""

from .graph import DocGemmaAgent, build_graph, GraphConfig, GRAPH_CONFIG
from .state import AgentState, ToolResult
from .state import AgentState as DocGemmaState  # backward compat alias
from . import prompts

__all__ = [
    "DocGemmaAgent",
    "build_graph",
    "GraphConfig",
    "GRAPH_CONFIG",
    "AgentState",
    "DocGemmaState",
    "ToolResult",
    "prompts",
]
