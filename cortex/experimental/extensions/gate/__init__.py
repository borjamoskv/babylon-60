from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.experimental.extensions.gate.core import SovereignGate, get_gate, reset_gate
    from cortex.experimental.extensions.gate.enums import ActionLevel, ActionStatus, GatePolicy
    from cortex.experimental.extensions.gate.errors import (
        GateError,
        GateExpired,
        GateInvalidSignature,
        GateNotApproved,
    )
    from cortex.experimental.extensions.gate.models import PendingAction

__all__ = [
    "ActionLevel",
    "ActionStatus",
    "GateError",
    "GateExpired",
    "GateInvalidSignature",
    "GateNotApproved",
    "GatePolicy",
    "PendingAction",
    "SovereignGate",
    "get_gate",
    "reset_gate",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "ActionLevel": ("cortex.experimental.extensions.gate.enums", "ActionLevel"),
    "ActionStatus": ("cortex.experimental.extensions.gate.enums", "ActionStatus"),
    "GateError": ("cortex.experimental.extensions.gate.errors", "GateError"),
    "GateExpired": ("cortex.experimental.extensions.gate.errors", "GateExpired"),
    "GateInvalidSignature": ("cortex.experimental.extensions.gate.errors", "GateInvalidSignature"),
    "GateNotApproved": ("cortex.experimental.extensions.gate.errors", "GateNotApproved"),
    "GatePolicy": ("cortex.experimental.extensions.gate.enums", "GatePolicy"),
    "PendingAction": ("cortex.experimental.extensions.gate.models", "PendingAction"),
    "SovereignGate": ("cortex.experimental.extensions.gate.core", "SovereignGate"),
    "get_gate": ("cortex.experimental.extensions.gate.core", "get_gate"),
    "reset_gate": ("cortex.experimental.extensions.gate.core", "reset_gate"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.experimental.extensions.gate' has no attribute {name!r}")
