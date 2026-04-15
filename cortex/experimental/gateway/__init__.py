"""CORTEX v5.0 — Gateway.

Sovereign Signal Bus and Cross-Axiom Orchestration.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.experimental.extensions.signals.bus import SignalBus
    from cortex.experimental.gateway.router import GatewayIntent, GatewayRequest, GatewayResponse, GatewayRouter

__all__ = [
    "SignalBus",
    "GatewayIntent",
    "GatewayRequest",
    "GatewayResponse",
    "GatewayRouter",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "SignalBus": ("cortex.experimental.extensions.signals.bus", "SignalBus"),
    "GatewayIntent": ("cortex.experimental.gateway.router", "GatewayIntent"),
    "GatewayRequest": ("cortex.experimental.gateway.router", "GatewayRequest"),
    "GatewayResponse": ("cortex.experimental.gateway.router", "GatewayResponse"),
    "GatewayRouter": ("cortex.experimental.gateway.router", "GatewayRouter"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.gateway' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
