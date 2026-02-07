"""Session management endpoints including WebSocket handler."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from ..models.events import ErrorEvent
from ..models.requests import CreateSessionRequest
from ..models.responses import (
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

    # Track running agent task so cancel can stop it
    agent_task: asyncio.Task | None = None
    send_queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def _run_agent_stream(event_gen) -> None:
        """Run agent event generator and push events to send queue."""
        try:
            async for event in event_gen:
                event_dict = event.model_dump(mode="json")
                await send_queue.put(event_dict)

                # If completion, also store the assistant message
                if event.event == "completion":
                    session.add_message("assistant", event.final_response)
        except asyncio.CancelledError:
            logger.info(f"Agent task cancelled for session {session_id}")
        except Exception as e:
            logger.exception(f"Agent task error for session {session_id}: {e}")
            await send_queue.put({
                "event": "error",
                "error_type": "execution_error",
                "message": str(e),
                "recoverable": False,
            })
        finally:
            # Close the generator to trigger _stream_execution's finally block,
            # which cancels the internal graph task and stops LLM generation.
            try:
                await event_gen.aclose()
            except Exception:
                pass
            await send_queue.put(None)  # Sentinel: agent done

    async def _send_loop() -> None:
        """Forward events from send queue to WebSocket."""
        while True:
            item = await send_queue.get()
            if item is None:
                break
            try:
                await websocket.send_json(item)
            except Exception:
                break

    try:
        while True:
            # If an agent task is running, we need to concurrently:
            # 1. Forward events from the agent to the client
            # 2. Listen for client messages (e.g. cancel)
            if agent_task is not None and not agent_task.done():
                sender = asyncio.create_task(_send_loop())
                try:
                    # Wait for either: client message OR agent completion
                    while not agent_task.done():
                        receive_task = asyncio.create_task(websocket.receive_text())
                        done, _ = await asyncio.wait(
                            {receive_task, agent_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        if receive_task in done:
                            raw_message = receive_task.result()
                            try:
                                message = json.loads(raw_message)
                            except json.JSONDecodeError:
                                continue

                            if message.get("action") == "cancel":
                                agent_task.cancel()
                                try:
                                    await agent_task
                                except asyncio.CancelledError:
                                    pass
                                session.status = SessionStatus.ACTIVE
                                session.pending_approval = None
                                # Don't send a fake completion — the frontend
                                # already resets its UI state in handleCancel().
                                break
                        else:
                            # Agent finished, cancel the pending receive
                            receive_task.cancel()
                            try:
                                await receive_task
                            except (asyncio.CancelledError, Exception):
                                pass
                finally:
                    # Drain remaining events from the queue
                    await sender
                    agent_task = None
                continue

            # Normal receive loop — no agent running
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
                event_gen = await _prepare_send_message(websocket, session, runner, data)
                if event_gen is not None:
                    send_queue = asyncio.Queue()
                    agent_task = asyncio.create_task(_run_agent_stream(event_gen))

            elif action == "approve_tool":
                event_gen = await _prepare_tool_approval(websocket, session, runner, approved=True)
                if event_gen is not None:
                    send_queue = asyncio.Queue()
                    agent_task = asyncio.create_task(_run_agent_stream(event_gen))

            elif action == "reject_tool":
                reason = data.get("reason")
                event_gen = await _prepare_tool_approval(
                    websocket, session, runner, approved=False, reason=reason
                )
                if event_gen is not None:
                    send_queue = asyncio.Queue()
                    agent_task = asyncio.create_task(_run_agent_stream(event_gen))

            elif action == "cancel":
                # Nothing running to cancel
                pass

            else:
                await websocket.send_json({
                    "event": "error",
                    "error_type": "unknown_action",
                    "message": f"Unknown action: {action}",
                    "recoverable": True,
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        if agent_task and not agent_task.done():
            agent_task.cancel()
    except Exception as e:
        logger.exception(f"WebSocket error for session {session_id}: {e}")
        if agent_task and not agent_task.done():
            agent_task.cancel()
        try:
            await websocket.send_json({
                "event": "error",
                "error_type": "internal_error",
                "message": str(e),
                "recoverable": False,
            })
        except Exception:
            pass


async def _prepare_send_message(
    websocket: WebSocket,
    session: Session,
    runner: AgentRunner,
    data: dict[str, Any],
):
    """Validate and prepare a send_message action.

    Returns an async generator of events, or None if validation failed
    (error already sent to client).
    """
    content = data.get("content", "").strip()
    if not content:
        await websocket.send_json({
            "event": "error",
            "error_type": "empty_message",
            "message": "Message content cannot be empty",
            "recoverable": True,
        })
        return None

    # Check if session is busy
    if session.status in (SessionStatus.PROCESSING, SessionStatus.WAITING_APPROVAL):
        await websocket.send_json({
            "event": "error",
            "error_type": "session_busy",
            "message": f"Session is {session.status.value}. Please wait or cancel.",
            "recoverable": True,
        })
        return None

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
            return None

    # Add user message to session
    session.add_message("user", content)

    # Build conversation history (last 2-3 turns for 4B model)
    history = _build_conversation_history(session, max_turns=3)

    # Return the event generator
    return runner.start_turn(
        session=session,
        user_input=content,
        image_data=image_data,
        conversation_history=history,
    )


async def _prepare_tool_approval(
    websocket: WebSocket,
    session: Session,
    runner: AgentRunner,
    approved: bool,
    reason: str | None = None,
):
    """Validate and prepare a tool approval/rejection.

    Returns an async generator of events, or None if validation failed.
    """
    if session.status != SessionStatus.WAITING_APPROVAL or not session.pending_approval:
        await websocket.send_json({
            "event": "error",
            "error_type": "no_pending_approval",
            "message": "No tool awaiting approval",
            "recoverable": True,
        })
        return None

    return runner.resume_with_approval(
        session=session,
        approved=approved,
        rejection_reason=reason,
    )


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
