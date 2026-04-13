"""Swarm entrypoints with lazy optional imports."""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

from cortex.swarm.autopulse import process_queue

if TYPE_CHECKING:
    from cortex.swarm.tensor_glial import TensorGlialLegion

__all__ = ["TensorGlialLegion", "start_swarm_daemon"]


def __getattr__(name: str) -> Any:
    """Resolve optional heavy swarm symbols lazily."""
    if name == "TensorGlialLegion":
        from cortex.swarm.tensor_glial import TensorGlialLegion

        return TensorGlialLegion
    raise AttributeError(name)


def start_swarm_daemon() -> threading.Thread:
    """Start the Swarm Autopoiesis engine in a background thread."""

    def run() -> None:
        asyncio.run(process_queue())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
