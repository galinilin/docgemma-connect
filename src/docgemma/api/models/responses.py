"""API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .session import SessionStatus


class MessageResponse(BaseModel):
    """Response representation of a message."""

    role: str
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Response representation of a session."""

    session_id: str
    status: SessionStatus
    messages: list[MessageResponse]
    pending_approval: dict[str, Any] | None = None
    current_node: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionResponse]
    total: int


class GraphNode(BaseModel):
    """A node in the graph visualization."""

    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Display label")
    status: str = Field(
        ...,
        description="Node status: pending, active, completed, skipped",
    )
    node_type: str = Field(
        default="default",
        description="Node type: decision, tool, llm, code",
    )


class GraphEdge(BaseModel):
    """An edge in the graph visualization."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str | None = Field(default=None, description="Edge label")
    active: bool = Field(default=False, description="Whether this edge is currently active")


class GraphStateResponse(BaseModel):
    """Response for graph state visualization."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    current_node: str | None = None
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class ToolInfo(BaseModel):
    """Information about an available tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    args: dict[str, str] = Field(..., description="Argument name -> description mapping")


class ToolListResponse(BaseModel):
    """Response for listing tools."""

    tools: list[ToolInfo]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    model_loaded: bool = False
    version: str = "0.1.0"
