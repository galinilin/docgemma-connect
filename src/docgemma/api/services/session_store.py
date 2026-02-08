"""In-memory session storage service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from ..models.session import Message, Session, SessionStatus


class SessionStore:
    """In-memory session storage.

    For production, this can be swapped with Redis or SQLite backend.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_all(self) -> list[Session]:
        """List all sessions."""
        return list(self._sessions.values())

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if session existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def update_status(self, session_id: str, status: SessionStatus) -> Session | None:
        """Update session status."""
        session = self._sessions.get(session_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
        return session

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message | None:
        """Add a message to a session."""
        session = self._sessions.get(session_id)
        if session:
            return session.add_message(role, content, metadata)
        return None

    def set_pending_approval(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        subtask_intent: str,
        checkpoint_id: str,
    ) -> Session | None:
        """Set a tool awaiting approval."""
        session = self._sessions.get(session_id)
        if session:
            session.set_pending_approval(
                tool_name=tool_name,
                tool_args=tool_args,
                subtask_intent=subtask_intent,
                checkpoint_id=checkpoint_id,
            )
        return session

    def clear_pending_approval(self, session_id: str) -> Session | None:
        """Clear pending approval."""
        session = self._sessions.get(session_id)
        if session:
            session.clear_pending_approval()
        return session

    def reset_for_new_turn(self, session_id: str) -> Session | None:
        """Reset turn-level state for a new user message."""
        session = self._sessions.get(session_id)
        if session:
            session.reset_for_new_turn()
        return session


# Global instance (singleton pattern for FastAPI dependency injection)
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
