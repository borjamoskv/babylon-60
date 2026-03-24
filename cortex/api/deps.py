"""
CORTEX v5.0 — API Dependencies.
Shared dependencies for FastAPI routes.
"""

from typing import Any

from fastapi import Request

from cortex.engine import CortexEngine
from cortex.extensions.timing import TimingTracker

__all__ = ["get_engine", "get_async_engine", "get_tracker"]


def get_engine(request: Request) -> CortexEngine:
    """Inject the legacy sync-wrapped engine from app state."""
    return request.app.state.engine


def get_async_engine(request: Request) -> Any:
    """Inject the primary async engine for the active storage mode."""
    primary_engine = getattr(request.app.state, "primary_async_engine", None)
    if primary_engine is not None:
        return primary_engine
    return request.app.state.async_engine


def get_tracker(request: Request) -> TimingTracker:
    """Inject the timing tracker from app state."""
    return request.app.state.tracker
