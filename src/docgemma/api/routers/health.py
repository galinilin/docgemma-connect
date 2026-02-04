"""Health check endpoint."""

from fastapi import APIRouter

from ..models.responses import HealthResponse

router = APIRouter(tags=["health"])

# Will be set by main.py on startup
_model_loaded: bool = False


def set_model_loaded(loaded: bool) -> None:
    """Set the model loaded status."""
    global _model_loaded
    _model_loaded = loaded


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse(
        status="ok",
        model_loaded=_model_loaded,
        version="0.1.0",
    )
