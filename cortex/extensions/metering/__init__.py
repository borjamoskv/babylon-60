"""CORTEX Metering — Usage tracking and quota enforcement for Memory-as-a-Service."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = ["PLAN_QUOTAS", "QuotaEnforcer", "UsageTracker"]

if TYPE_CHECKING:
    from cortex.extensions.metering.quotas import PLAN_QUOTAS, QuotaEnforcer
    from cortex.extensions.metering.tracker import UsageTracker


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "PLAN_QUOTAS": ("cortex.extensions.metering.quotas", "PLAN_QUOTAS"),
    "QuotaEnforcer": ("cortex.extensions.metering.quotas", "QuotaEnforcer"),
    "UsageTracker": ("cortex.extensions.metering.tracker", "UsageTracker"),
}


def __getattr__(name: str) -> object:
    """Lazily expose the public metering symbols."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'cortex.extensions.metering' has no attribute {name!r}")

    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
