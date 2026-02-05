"""WebSocket event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base class for all WebSocket events."""

    event: str = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NodeStartEvent(BaseEvent):
    """Event when a graph node starts execution."""

    event: Literal["node_start"] = "node_start"
    node_id: str = Field(..., description="Node identifier")
    node_label: str = Field(..., description="Human-readable node name")


class NodeEndEvent(BaseEvent):
    """Event when a graph node completes execution."""

    event: Literal["node_end"] = "node_end"
    node_id: str = Field(..., description="Node identifier")
    node_label: str = Field(..., description="Human-readable node name")
    duration_ms: float = Field(..., description="Execution time in milliseconds")


class ToolApprovalRequestEvent(BaseEvent):
    """Event requesting user approval for a tool execution."""

    event: Literal["tool_approval_request"] = "tool_approval_request"
    tool_name: str = Field(..., description="Name of the tool")
    tool_args: dict[str, Any] = Field(..., description="Tool arguments")
    subtask_intent: str = Field(..., description="What this tool call aims to achieve")


class ToolExecutionStartEvent(BaseEvent):
    """Event when tool execution begins."""

    event: Literal["tool_execution_start"] = "tool_execution_start"
    tool_name: str = Field(..., description="Name of the tool")
    tool_args: dict[str, Any] = Field(..., description="Tool arguments")


class ToolExecutionEndEvent(BaseEvent):
    """Event when tool execution completes."""

    event: Literal["tool_execution_end"] = "tool_execution_end"
    tool_name: str = Field(..., description="Name of the tool")
    success: bool = Field(..., description="Whether execution succeeded")
    result: dict[str, Any] = Field(..., description="Tool result")
    duration_ms: float = Field(..., description="Execution time in milliseconds")


class StreamingTextEvent(BaseEvent):
    """Event for incremental text generation."""

    event: Literal["streaming_text"] = "streaming_text"
    text: str = Field(..., description="Incremental text chunk")
    node_id: str = Field(..., description="Node generating the text")


class CompletionEvent(BaseEvent):
    """Event when agent completes processing."""

    event: Literal["completion"] = "completion"
    final_response: str = Field(..., description="Final agent response")
    tool_calls_made: int = Field(default=0, description="Number of tool calls made")


class ErrorEvent(BaseEvent):
    """Event when an error occurs."""

    event: Literal["error"] = "error"
    error_type: str = Field(..., description="Error type/category")
    message: str = Field(..., description="Error message")
    recoverable: bool = Field(
        default=True,
        description="Whether the session can continue",
    )


# Union type for all events (useful for type hints)
AgentEvent = (
    NodeStartEvent
    | NodeEndEvent
    | ToolApprovalRequestEvent
    | ToolExecutionStartEvent
    | ToolExecutionEndEvent
    | StreamingTextEvent
    | CompletionEvent
    | ErrorEvent
)
