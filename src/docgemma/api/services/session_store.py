"""Session storage service with optional disk persistence."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.session import Message, Session, SessionStatus

logger = logging.getLogger(__name__)


class SessionStore:
    """Session storage with in-memory cache and optional JSON-file persistence.

    When ``data_dir`` is provided, each session is persisted as
    ``{data_dir}/{session_id}.json``. The in-memory dict acts as a fast cache;
    every mutation is written through to disk.

    When ``data_dir`` is ``None`` (the default), the store is purely in-memory
    — useful for tests.
    """

    def __init__(self, data_dir: Path | None = None):
        self._sessions: dict[str, Session] = {}
        self._data_dir = data_dir

        if self._data_dir is not None:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Load every ``*.json`` file from *data_dir* into the cache."""
        assert self._data_dir is not None
        count = 0
        for path in self._data_dir.glob("*.json"):
            try:
                session = Session.model_validate_json(path.read_text())
                # Checkpoint IDs are ephemeral — clear stale approval state
                if session.pending_approval is not None:
                    session.pending_approval = None
                    session.status = SessionStatus.ACTIVE
                self._sessions[session.session_id] = session
                count += 1
            except Exception:
                logger.warning("Failed to load session file %s, skipping", path)
        if count:
            logger.info("Loaded %d session(s) from %s", count, self._data_dir)

    def _save(self, session: Session) -> None:
        """Atomically persist *session* to disk (write .tmp then rename)."""
        if self._data_dir is None:
            return
        target = self._data_dir / f"{session.session_id}.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(session.model_dump_json(indent=2))
        os.replace(tmp, target)

    def _delete_file(self, session_id: str) -> None:
        """Remove the JSON file for *session_id* if it exists."""
        if self._data_dir is None:
            return
        path = self._data_dir / f"{session_id}.json"
        path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        self._save(session)
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
            self._delete_file(session_id)
            return True
        return False

    def update_status(self, session_id: str, status: SessionStatus) -> Session | None:
        """Update session status."""
        session = self._sessions.get(session_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
            self._save(session)
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
            msg = session.add_message(role, content, metadata)
            self._save(session)
            return msg
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
            self._save(session)
        return session

    def clear_pending_approval(self, session_id: str) -> Session | None:
        """Clear pending approval."""
        session = self._sessions.get(session_id)
        if session:
            session.clear_pending_approval()
            self._save(session)
        return session

    def reset_for_new_turn(self, session_id: str) -> Session | None:
        """Reset turn-level state for a new user message."""
        session = self._sessions.get(session_id)
        if session:
            session.reset_for_new_turn()
            self._save(session)
        return session


# Global instance (singleton pattern for FastAPI dependency injection)
_session_store: SessionStore | None = None


def init_session_store(data_dir: Path | None = None) -> SessionStore:
    """Create and set the global session store. Call once during startup."""
    global _session_store
    _session_store = SessionStore(data_dir=data_dir)
    return _session_store


def get_session_store() -> SessionStore:
    """Get the global session store instance (used by FastAPI Depends)."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
