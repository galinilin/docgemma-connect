"""API configuration settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class APIConfig:
    """Configuration for the DocGemma API."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS settings
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = field(default_factory=lambda: ["*"])

    # Model settings
    # Model configuration is handled via environment variables:
    # - DOCGEMMA_ENDPOINT: vLLM or OpenAI-compatible API endpoint
    # - DOCGEMMA_API_KEY: API key for authentication
    # - DOCGEMMA_MODEL: Model name (default: google/medgemma-1.5-4b-it)
    load_model_on_startup: bool = True
    enable_tool_approval: bool = True

    # Session persistence
    sessions_dir: str = "data/sessions"

    # Rate limiting (for future)
    max_sessions: int = 100
    max_messages_per_session: int = 1000

    @classmethod
    def from_env(cls) -> APIConfig:
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("DOCGEMMA_HOST", "0.0.0.0"),
            port=int(os.getenv("DOCGEMMA_PORT", "8000")),
            debug=os.getenv("DOCGEMMA_DEBUG", "").lower() in ("true", "1", "yes"),
            cors_origins=os.getenv("DOCGEMMA_CORS_ORIGINS", "*").split(","),
            load_model_on_startup=os.getenv("DOCGEMMA_LOAD_MODEL", "true").lower()
            in ("true", "1", "yes"),
            enable_tool_approval=os.getenv("DOCGEMMA_TOOL_APPROVAL", "true").lower()
            in ("true", "1", "yes"),
            sessions_dir=os.getenv("DOCGEMMA_SESSIONS_DIR", "data/sessions"),
        )


# Global config instance
_config: APIConfig | None = None


def get_config() -> APIConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = APIConfig.from_env()
    return _config
