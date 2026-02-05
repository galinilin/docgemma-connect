"""Session management endpoints including WebSocket handler."""

from __future__ import annotations

import base64
import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from ..models.events import ErrorEvent
from ..models.requests import CreateSessionRequest
from ..models.responses import (
    GraphEdge,
    GraphNode,
    GraphStateResponse,
    MessageResponse,
    SessionListResponse,
    SessionResponse,
)
from ..models.session import Session, SessionStatus
from ..services.session_store import SessionStore, get_session_store

if TYPE_CHECKING:
    from ..services.agent_runner import AgentRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Will be set by main.py on startup
_agent_runner: AgentRunner | None = None


def set_agent_runner(runner: AgentRunner) -> None:
    """Set the global agent runner instance."""
    global _agent_runner
    _agent_runner = runner


def get_agent_runner() -> AgentRunner | None:
    """Get the global agent runner instance."""
    return _agent_runner


def _session_to_response(session: Session) -> SessionResponse:
    """Convert Session model to response schema."""
    return SessionResponse(
        session_id=session.session_id,
        status=session.status,
        messages=[
            MessageResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                metadata=msg.metadata,
            )
            for msg in session.messages
        ],
        pending_approval=session.pending_approval.model_dump() if session.pending_approval else None,
        current_node=session.current_node,
        completed_nodes=session.completed_nodes,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest | None = None,
    store: SessionStore = Depends(get_session_store),
) -> SessionResponse:
    """Create a new chat session."""
    session = store.create()
    return _session_to_response(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    store: SessionStore = Depends(get_session_store),
) -> SessionListResponse:
    """List all active sessions."""
    sessions = store.list_all()
    return SessionListResponse(
        sessions=[_session_to_response(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> SessionResponse:
    """Get a session by ID."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _session_to_response(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> None:
    """Delete a session."""
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> list[MessageResponse]:
    """Get conversation history for a session."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return [
        MessageResponse(
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            metadata=msg.metadata,
        )
        for msg in session.messages
    ]


@router.get("/{session_id}/graph", response_model=GraphStateResponse)
async def get_graph_state(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> GraphStateResponse:
    """Get graph state for visualization.

    Returns the current state of the agent graph including:
    - All nodes with their status (pending/active/completed)
    - Edges between nodes with active state
    - Current executing node
    - Subtasks and tool results
    """
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Import here to avoid circular imports
    from ...agent.graph import GRAPH_EDGES, GRAPH_NODES

    # Build nodes with status
    nodes = []
    for node_def in GRAPH_NODES:
        status = "pending"
        if node_def["id"] in session.completed_nodes:
            status = "completed"
        elif node_def["id"] == session.current_node:
            status = "active"

        nodes.append(
            GraphNode(
                id=node_def["id"],
                label=node_def["label"],
                status=status,
                node_type=node_def["type"],
            )
        )

    # Build edges with active state
    edges = []
    for edge_def in GRAPH_EDGES:
        active = (
            edge_def["source"] in session.completed_nodes
            and (
                edge_def["target"] == session.current_node
                or edge_def["target"] in session.completed_nodes
            )
        )
        edges.append(
            GraphEdge(
                source=edge_def["source"],
                target=edge_def["target"],
                label=edge_def["label"],
                active=active,
            )
        )

    return GraphStateResponse(
        nodes=nodes,
        edges=edges,
        current_node=session.current_node,
        subtasks=[],  # Would need agent runner to get these
        tool_results=[],
    )


# =============================================================================
# WebSocket Handler
# =============================================================================


@router.websocket("/{session_id}/ws")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """WebSocket endpoint for real-time chat.

    Client -> Server Messages:
        {"action": "send_message", "data": {"content": "...", "image_base64": null}}
        {"action": "approve_tool", "data": {}}
        {"action": "reject_tool", "data": {"reason": "optional"}}
        {"action": "cancel", "data": {}}

    Server -> Client Events:
        {"event": "node_start", ...}
        {"event": "node_end", ...}
        {"event": "tool_approval_request", ...}
        {"event": "tool_execution_start", ...}
        {"event": "tool_execution_end", ...}
        {"event": "streaming_text", ...}
        {"event": "completion", ...}
        {"event": "error", ...}
    """
    await websocket.accept()

    store = get_session_store()
    session = store.get(session_id)

    if not session:
        await websocket.send_json({
            "event": "error",
            "error_type": "session_not_found",
            "message": f"Session '{session_id}' not found",
            "recoverable": False,
        })
        await websocket.close(code=4004)
        return

    runner = get_agent_runner()
    if not runner:
        await websocket.send_json({
            "event": "error",
            "error_type": "model_not_loaded",
            "message": "Model not loaded. Please wait for server to initialize.",
            "recoverable": False,
        })
        await websocket.close(code=4003)
        return

    try:
        while True:
            # Wait for client message
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "event": "error",
                    "error_type": "invalid_json",
                    "message": "Invalid JSON message",
                    "recoverable": True,
                })
                continue

            action = message.get("action")
            data = message.get("data", {})

            if action == "send_message":
                await _handle_send_message(websocket, session, runner, data)

            elif action == "approve_tool":
                await _handle_tool_approval(websocket, session, runner, approved=True)

            elif action == "reject_tool":
                reason = data.get("reason")
                await _handle_tool_approval(
                    websocket, session, runner, approved=False, reason=reason
                )

            elif action == "cancel":
                # Cancel current operation - just reset session status
                session.status = SessionStatus.ACTIVE
                session.pending_approval = None
                await websocket.send_json({
                    "event": "completion",
                    "final_response": "Operation cancelled.",
                    "tool_calls_made": 0,
                })

            else:
                await websocket.send_json({
                    "event": "error",
                    "error_type": "unknown_action",
                    "message": f"Unknown action: {action}",
                    "recoverable": True,
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "event": "error",
                "error_type": "internal_error",
                "message": str(e),
                "recoverable": False,
            })
        except Exception:
            pass


async def _handle_send_message(
    websocket: WebSocket,
    session: Session,
    runner: AgentRunner,
    data: dict[str, Any],
) -> None:
    """Handle a send_message action."""
    content = data.get("content", "").strip()
    if not content:
        await websocket.send_json({
            "event": "error",
            "error_type": "empty_message",
            "message": "Message content cannot be empty",
            "recoverable": True,
        })
        return

    # Check if session is busy
    if session.status in (SessionStatus.PROCESSING, SessionStatus.WAITING_APPROVAL):
        await websocket.send_json({
            "event": "error",
            "error_type": "session_busy",
            "message": f"Session is {session.status.value}. Please wait or cancel.",
            "recoverable": True,
        })
        return

    # Handle optional image
    image_data = None
    image_base64 = data.get("image_base64")
    if image_base64:
        try:
            image_data = base64.b64decode(image_base64)
        except Exception:
            await websocket.send_json({
                "event": "error",
                "error_type": "invalid_image",
                "message": "Invalid base64 image data",
                "recoverable": True,
            })
            return

    # Add user message to session
    session.add_message("user", content)

    # Build conversation history (last 2-3 turns for 4B model)
    history = _build_conversation_history(session, max_turns=3)

    # Stream agent execution events
    async for event in runner.start_turn(
        session=session,
        user_input=content,
        image_data=image_data,
        conversation_history=history,
    ):
        await websocket.send_json(event.model_dump(mode="json"))

        # If completion, add assistant message to session
        if event.event == "completion":
            session.add_message("assistant", event.final_response)


async def _handle_tool_approval(
    websocket: WebSocket,
    session: Session,
    runner: AgentRunner,
    approved: bool,
    reason: str | None = None,
) -> None:
    """Handle tool approval or rejection."""
    if session.status != SessionStatus.WAITING_APPROVAL or not session.pending_approval:
        await websocket.send_json({
            "event": "error",
            "error_type": "no_pending_approval",
            "message": "No tool awaiting approval",
            "recoverable": True,
        })
        return

    # Stream remaining execution
    async for event in runner.resume_with_approval(
        session=session,
        approved=approved,
        rejection_reason=reason,
    ):
        await websocket.send_json(event.model_dump(mode="json"))

        # If completion, add assistant message
        if event.event == "completion":
            session.add_message("assistant", event.final_response)


def _build_conversation_history(
    session: Session,
    max_turns: int = 3,
) -> list[dict[str, str]]:
    """Build conversation history for context.

    Only includes user and assistant messages, limited to recent turns.
    """
    history = []
    turn_count = 0

    # Go through messages in reverse to get most recent
    for msg in reversed(session.messages):
        if msg.role in ("user", "assistant"):
            history.insert(0, {"role": msg.role, "content": msg.content})
            if msg.role == "user":
                turn_count += 1
                if turn_count >= max_turns:
                    break

    # Remove the current (last) user message if present - it's passed separately
    if history and history[-1]["role"] == "user":
        history = history[:-1]

    return history
