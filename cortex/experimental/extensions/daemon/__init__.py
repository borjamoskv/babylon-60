"""
CORTEX Daemon — Package init (lazy-loaded).

Re-exports from sub-modules for backward compatibility.
Uses __getattr__ to avoid eager loading of heavyweight dependencies
(e.g., watchdog via core.py → ast_oracle.py). This prevents
ModuleNotFoundError cascades when importing lightweight daemon
submodules like epistemic_breaker or models.

Ghost #4731: The previous eager init caused cortex.cli store to crash
because any `from cortex.experimental.extensions.daemon.X import Y` triggered the full import
chain including optional dependencies.
"""

from __future__ import annotations

import importlib
import socket  # noqa: F401
import ssl  # noqa: F401 — re-export for backward compat (tests patch via cortex.daemon.ssl)
import time  # noqa: F401
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.experimental.extensions.daemon.core import MoskvDaemon
    from cortex.experimental.extensions.daemon.models import (
        BUNDLE_ID,
        DEFAULT_COOLDOWN,
        DEFAULT_INTERVAL,
        DEFAULT_MEMORY_STALE_HOURS,
        DEFAULT_STALE_HOURS,
        STATUS_FILE,
        CertAlert,
        DaemonStatus,
        DiskAlert,
        EngineHealthAlert,
        EntropyAlert,
        GhostAlert,
        MejoraloAlert,
        MemoryAlert,
        PerceptionAlert,
        SiteStatus,
    )
    from cortex.experimental.extensions.daemon.monitors import (
        CertMonitor,
        DiskMonitor,
        EngineHealthCheck,
        EntropyMonitor,
        GhostWatcher,
        MemorySyncer,
        PerceptionMonitor,
        SiteMonitor,
    )
    from cortex.experimental.extensions.daemon.notifier import Notifier

__all__ = [
    # core
    "MoskvDaemon",
    # models
    "BUNDLE_ID",
    "DEFAULT_COOLDOWN",
    "DEFAULT_INTERVAL",
    "DEFAULT_MEMORY_STALE_HOURS",
    "DEFAULT_STALE_HOURS",
    "STATUS_FILE",
    "CertAlert",
    "DaemonStatus",
    "DiskAlert",
    "EngineHealthAlert",
    "EntropyAlert",
    "GhostAlert",
    "MejoraloAlert",
    "MemoryAlert",
    "PerceptionAlert",
    "SiteStatus",
    # monitors
    "CertMonitor",
    "DiskMonitor",
    "EngineHealthCheck",
    "EntropyMonitor",
    "GhostWatcher",
    "MemorySyncer",
    "PerceptionMonitor",
    "SiteMonitor",
    # notifier
    "Notifier",
]

# Lazy-load map: attribute name → (module_path, attr_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # core
    "MoskvDaemon": ("cortex.experimental.extensions.daemon.core", "MoskvDaemon"),
    # models
    "BUNDLE_ID": ("cortex.experimental.extensions.daemon.models", "BUNDLE_ID"),
    "DEFAULT_COOLDOWN": ("cortex.experimental.extensions.daemon.models", "DEFAULT_COOLDOWN"),
    "DEFAULT_INTERVAL": ("cortex.experimental.extensions.daemon.models", "DEFAULT_INTERVAL"),
    "DEFAULT_MEMORY_STALE_HOURS": ("cortex.experimental.extensions.daemon.models", "DEFAULT_MEMORY_STALE_HOURS"),
    "DEFAULT_STALE_HOURS": ("cortex.experimental.extensions.daemon.models", "DEFAULT_STALE_HOURS"),
    "STATUS_FILE": ("cortex.experimental.extensions.daemon.models", "STATUS_FILE"),
    "CertAlert": ("cortex.experimental.extensions.daemon.models", "CertAlert"),
    "DaemonStatus": ("cortex.experimental.extensions.daemon.models", "DaemonStatus"),
    "DiskAlert": ("cortex.experimental.extensions.daemon.models", "DiskAlert"),
    "EngineHealthAlert": ("cortex.experimental.extensions.daemon.models", "EngineHealthAlert"),
    "EntropyAlert": ("cortex.experimental.extensions.daemon.models", "EntropyAlert"),
    "GhostAlert": ("cortex.experimental.extensions.daemon.models", "GhostAlert"),
    "MejoraloAlert": ("cortex.experimental.extensions.daemon.models", "MejoraloAlert"),
    "MemoryAlert": ("cortex.experimental.extensions.daemon.models", "MemoryAlert"),
    "PerceptionAlert": ("cortex.experimental.extensions.daemon.models", "PerceptionAlert"),
    "SiteStatus": ("cortex.experimental.extensions.daemon.models", "SiteStatus"),
    # monitors
    "CertMonitor": ("cortex.experimental.extensions.daemon.monitors", "CertMonitor"),
    "DiskMonitor": ("cortex.experimental.extensions.daemon.monitors", "DiskMonitor"),
    "EngineHealthCheck": ("cortex.experimental.extensions.daemon.monitors", "EngineHealthCheck"),
    "EntropyMonitor": ("cortex.experimental.extensions.daemon.monitors", "EntropyMonitor"),
    "GhostWatcher": ("cortex.experimental.extensions.daemon.monitors", "GhostWatcher"),
    "MemorySyncer": ("cortex.experimental.extensions.daemon.monitors", "MemorySyncer"),
    "PerceptionMonitor": ("cortex.experimental.extensions.daemon.monitors", "PerceptionMonitor"),
    "SiteMonitor": ("cortex.experimental.extensions.daemon.monitors", "SiteMonitor"),
    # notifier
    "Notifier": ("cortex.experimental.extensions.daemon.notifier", "Notifier"),
}


def __getattr__(name: str) -> object:
    """Lazy-load daemon symbols on first access (PEP 562)."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        # Cache on module dict for O(1) subsequent access
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.experimental.extensions.daemon' has no attribute {name!r}")
