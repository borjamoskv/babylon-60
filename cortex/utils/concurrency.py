# [C5-REAL] Exergy-Maximized
"""Concurrency utilities for loop-safe lock management."""

from __future__ import annotations

import asyncio
from typing import Any


def get_loop_lock(
    instance: Any,
    cache_attr: str,
    fallback_attr: str,
) -> asyncio.Lock:
    """Retrieve or create a loop-specific Lock, falling back to a thread-safe lock if no loop runs."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if not hasattr(instance, fallback_attr):
            setattr(instance, fallback_attr, asyncio.Lock())
        return getattr(instance, fallback_attr)

    if not hasattr(instance, cache_attr):
        setattr(instance, cache_attr, {})

    locks = getattr(instance, cache_attr)
    if loop not in locks:
        locks[loop] = asyncio.Lock()
    return locks[loop]
