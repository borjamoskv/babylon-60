"""Legacy memories route shim.

The public compatibility surface for ``/v1/memories/*`` is the redirect in
``cortex.api.core.memory_redirect``. This module intentionally no longer
duplicates the mounted ``/v1/facts`` handlers.
"""

from fastapi import APIRouter

__all__ = ["router"]

router = APIRouter(prefix="/v1/memories", tags=["memories"])
