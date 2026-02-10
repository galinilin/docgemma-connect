"""FastAPI application factory for DocGemma API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import APIConfig, get_config
from .routers import health_router, patients_router, sessions_router
from .routers.health import set_model_loaded
from .routers.sessions import set_agent_runner

if TYPE_CHECKING:
    from ..model import DocGemma

logger = logging.getLogger(__name__)


class SPAStaticFiles(StaticFiles):
    """Static files handler that falls back to index.html for SPA routing."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise

# Global model instance
_model: DocGemma | None = None

from dotenv import load_dotenv
load_dotenv()

def get_model() -> DocGemma | None:
    """Get the loaded model instance."""
    return _model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    global _model

    config = get_config()

    if config.load_model_on_startup:
        logger.info("Initializing DocGemma model...")
        try:
            # Import here to avoid loading torch at module level
            from ..model import DocGemma
            from ..agent.prompts import SYSTEM_PROMPT
            from .services.agent_runner import AgentRunner

            _model = DocGemma(system_prompt=SYSTEM_PROMPT)

            # Create and set the agent runner
            runner = AgentRunner(
                model=_model,
                enable_tool_approval=config.enable_tool_approval,
            )
            set_agent_runner(runner)
            set_model_loaded(True)

            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Continue without model - WebSocket will return appropriate error
    else:
        logger.info("Skipping model load (DOCGEMMA_LOAD_MODEL=false)")

    yield

    # Cleanup on shutdown
    if _model is not None:
        logger.info("Shutting down...")
        # Model cleanup if needed
        _model = None


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional configuration. If None, loads from environment.

    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = get_config()

    app = FastAPI(
        title="DocGemma API",
        description="Medical AI assistant API powered by MedGemma",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.cors_allow_credentials,
        allow_methods=config.cors_allow_methods,
        allow_headers=config.cors_allow_headers,
    )

    # Register routers
    app.include_router(health_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(patients_router, prefix="/api")

    # Serve built frontend SPA (no-op if static/ doesn't exist, e.g. during dev)
    static_dir = Path(__file__).resolve().parent.parent.parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/", SPAStaticFiles(directory=str(static_dir), html=True), name="spa")

    return app


# Default app instance for uvicorn
app = create_app()


def main():
    """Entry point for the docgemma-serve command."""
    import uvicorn

    config = get_config()
    uvicorn.run(
        "docgemma.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )


if __name__ == "__main__":
    main()
