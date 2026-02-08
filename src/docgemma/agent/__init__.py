"""DocGemma Agent - LangGraph-based medical AI assistant (v2: 4-way triage)."""

from .graph import DocGemmaAgent, build_graph, GraphConfig, GRAPH_CONFIG
from .state import DocGemmaState, Subtask, ToolResult
from . import prompts

__all__ = [
    "DocGemmaAgent",
    "build_graph",
    "GraphConfig",
    "GRAPH_CONFIG",
    "DocGemmaState",
    "Subtask",
    "ToolResult",
    "prompts",
]
