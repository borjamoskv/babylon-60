"""Sync Engine Package.

Exposes the main sync functions and result types.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.experimental.extensions.sync.common import (
        AGENT_DIR,
        CORTEX_DIR,
        MEMORY_DIR,
        SYNC_STATE_FILE,
        SyncResult,
        WritebackResult,
    )
    from cortex.experimental.extensions.sync.common import (
        db_content_hash as _db_content_hash,
    )
    from cortex.experimental.extensions.sync.common import (
        file_hash as _file_hash,
    )
    from cortex.experimental.extensions.sync.obsidian import export_obsidian
    from cortex.experimental.extensions.sync.read import sync_memory
    from cortex.experimental.extensions.sync.snapshot import export_snapshot
    from cortex.experimental.extensions.sync.write import export_to_json

__all__ = [
    "sync_memory",
    "export_to_json",
    "export_snapshot",
    "export_obsidian",
    "SyncResult",
    "WritebackResult",
    "MEMORY_DIR",
    "AGENT_DIR",
    "CORTEX_DIR",
    "SYNC_STATE_FILE",
    "_file_hash",
    "_db_content_hash",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "sync_memory": ("cortex.experimental.extensions.sync.read", "sync_memory"),
    "export_to_json": ("cortex.experimental.extensions.sync.write", "export_to_json"),
    "export_snapshot": ("cortex.experimental.extensions.sync.snapshot", "export_snapshot"),
    "export_obsidian": ("cortex.experimental.extensions.sync.obsidian", "export_obsidian"),
    "SyncResult": ("cortex.experimental.extensions.sync.common", "SyncResult"),
    "WritebackResult": ("cortex.experimental.extensions.sync.common", "WritebackResult"),
    "MEMORY_DIR": ("cortex.experimental.extensions.sync.common", "MEMORY_DIR"),
    "AGENT_DIR": ("cortex.experimental.extensions.sync.common", "AGENT_DIR"),
    "CORTEX_DIR": ("cortex.experimental.extensions.sync.common", "CORTEX_DIR"),
    "SYNC_STATE_FILE": ("cortex.experimental.extensions.sync.common", "SYNC_STATE_FILE"),
    "_file_hash": ("cortex.experimental.extensions.sync.common", "file_hash"),
    "_db_content_hash": ("cortex.experimental.extensions.sync.common", "db_content_hash"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'cortex.experimental.extensions.sync' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
