"""Session data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status states."""

    ACTIVE = "active"
    PROCESSING = "processing"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"


class Message(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: user, assistant, or tool")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (tool_name, tool_args, etc.)",
    )


class PendingToolApproval(BaseModel):
    """Information about a tool awaiting user approval."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    tool_args: dict[str, Any] = Field(..., description="Arguments for the tool")
    subtask_intent: str = Field(..., description="What this tool call is trying to achieve")
    checkpoint_id: str = Field(..., description="LangGraph checkpoint ID for resuming")


class Session(BaseModel):
    """A chat session with the DocGemma agent."""

    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)
    messages: list[Message] = Field(default_factory=list)
    pending_approval: PendingToolApproval | None = Field(
        default=None,
        description="Tool awaiting approval, if any",
    )
    selected_patient_id: str | None = Field(
        default=None,
        description="Last patient selected by the user (persisted across reloads)",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to the session."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg

    def set_pending_approval(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        subtask_intent: str,
        checkpoint_id: str,
    ) -> None:
        """Set a tool awaiting approval."""
        self.pending_approval = PendingToolApproval(
            tool_name=tool_name,
            tool_args=tool_args,
            subtask_intent=subtask_intent,
            checkpoint_id=checkpoint_id,
        )
        self.status = SessionStatus.WAITING_APPROVAL
        self.updated_at = datetime.utcnow()

    def clear_pending_approval(self) -> None:
        """Clear pending approval after user response."""
        self.pending_approval = None
        self.status = SessionStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def reset_for_new_turn(self) -> None:
        """Reset turn-level state for a new user message."""
        self.updated_at = datetime.utcnow()
