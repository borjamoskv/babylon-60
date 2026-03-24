"""Bicameral Dispatcher — CORTEX v8.0.
Decouples Fast-Path (Vector/Search) from Slow-Path (Ledger/Persistence).
Ω₁₃: Thermodynamic optimization via asynchronous bus separation.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("cortex.bicameral")

class BicameralDispatcher:
    """Manages the dual-bus execution of cognitive operations."""

    def __init__(self):
        self._fast_bus: dict[str, Callable] = {}
        # Per-operation slow handlers: dict[operation_name, list[Callable]]
        # The sentinel key "_all" is used by register_slow() to attach to every operation.
        self._slow_bus: dict[str, list[Callable]] = defaultdict(list)
        self._background_tasks: set[asyncio.Task] = set()

    def register_fast(self, name: str, func: Callable):
        """Register a high-priority, low-latency operation."""
        self._fast_bus[name] = func

    def register_slow(self, func: Callable, name: str = "_all"):
        """Register a background persistence or audit operation.

        If *name* is given, func is only triggered when that operation is dispatched.
        The default sentinel ``_all`` triggers the handler for every dispatched operation.
        """
        self._slow_bus[name].append(func)

    async def dispatch(self, operation: str, *args, **kwargs) -> Any:
        """Execute the fast-path immediately and trigger the slow-path in background."""
        if operation not in self._fast_bus:
            raise KeyError(f"Operation '{operation}' not registered in Fast-Bus.")

        # 1. Execute Fast-Path (Vector Search, L1 Cache)
        result = await self._fast_bus[operation](*args, **kwargs)

        # 2. Trigger Slow-Path — operation-specific handlers + catch-all handlers
        slow_ops: list[Callable] = list(self._slow_bus.get(operation, []))
        slow_ops.extend(self._slow_bus.get("_all", []))

        for slow_op in slow_ops:
            task = asyncio.create_task(self._safe_execute_slow(slow_op, *args, **kwargs))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return result

    async def _safe_execute_slow(self, func: Callable, *args, **kwargs):
        """Internal helper to ensure background tasks don't crash the engine."""
        try:
            await func(*args, **kwargs)
        except Exception:
            logger.exception("Slow-bus execution failed")

    async def shutdown(self):
        """Await all pending background tasks before closing."""
        if self._background_tasks:
            logger.info("Awaiting %d slow-bus tasks...", len(self._background_tasks))
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
