"""API routers."""

from .health import router as health_router
from .patients import router as patients_router
from .sessions import router as sessions_router

__all__ = [
    "health_router",
    "patients_router",
    "sessions_router",
]
