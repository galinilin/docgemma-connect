"""API request schemas."""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    # No required fields - session is created empty
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""

    content: str = Field(..., description="User message content")
    image_base64: str | None = Field(
        default=None,
        description="Optional base64-encoded image data",
    )


class ToolApprovalRequest(BaseModel):
    """Request to approve or reject a tool execution."""

    approved: bool = Field(..., description="Whether to approve the tool execution")
    reason: str | None = Field(
        default=None,
        description="Optional reason for rejection",
    )
