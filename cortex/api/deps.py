"""CORTEX v5.0 — API Dependencies.
Shared dependencies for FastAPI routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request

from cortex.services.public_memory import PublicMemoryService

__all__ = ["get_engine", "get_async_engine", "get_public_memory_service", "get_tracker"]

if TYPE_CHECKING:
    from cortex.engine import CortexEngine
    from cortex.engine import CortexEngine as AsyncCortexEngine
    from cortex.extensions.timing import TimingTracker


def get_engine(request: Request) -> CortexEngine:
    """Inject the legacy sync-wrapped engine from app state."""
    return request.app.state.engine


def get_async_engine(request: Request) -> AsyncCortexEngine:
    """Inject the native async engine (Wave 5)."""
    return request.app.state.async_engine


def get_public_memory_service(
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> PublicMemoryService:
    """Inject the shared public-memory service backed by the async engine."""
    return PublicMemoryService(engine)


def get_tracker(request: Request) -> TimingTracker:
    """Inject the timing tracker from app state."""
    return request.app.state.tracker
