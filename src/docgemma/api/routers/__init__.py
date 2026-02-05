"""API routers."""

from .health import router as health_router
from .patients import router as patients_router
from .sessions import router as sessions_router
from .tools import router as tools_router

__all__ = [
    "health_router",
    "patients_router",
    "sessions_router",
    "tools_router",
]
