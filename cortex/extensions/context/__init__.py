"""CORTEX v5.0 — Context Engine.

Ambient signal collection, multi-signal inference for contextual intelligence,
and HiAgent subgoal compression for long-horizon loops.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["ContextCollector", "ContextInference", "HiAgentTraceManager"]

if TYPE_CHECKING:
    from cortex.extensions.context.collector import ContextCollector
    from cortex.extensions.context.hiagent import HiAgentTraceManager
    from cortex.extensions.context.inference import ContextInference


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "ContextCollector": ("cortex.extensions.context.collector", "ContextCollector"),
    "ContextInference": ("cortex.extensions.context.inference", "ContextInference"),
    "HiAgentTraceManager": ("cortex.extensions.context.hiagent", "HiAgentTraceManager"),
}


def __getattr__(name: str) -> object:
    """Lazily expose the public context symbols."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'cortex.extensions.context' has no attribute {name!r}")

    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
