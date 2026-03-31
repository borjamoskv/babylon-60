"""Compatibility shim for legacy handoff source checks.

The real handoff implementation lives in
``cortex.extensions.agents.handoff``. This module keeps older import paths
and source-based tests working without duplicating the implementation.
"""

from __future__ import annotations

from cortex.extensions.agents.handoff import (  # noqa: F401
    DEFAULT_HANDOFF_PATH,
    MAX_DECISIONS,
    MAX_ERRORS,
    MAX_GHOSTS,
    generate_handoff,
    load_handoff,
    save_handoff,
)

HANDOFF_VERSION = "1.3"
COGNITIVE_FINGERPRINT_KEY = "cognitive_fingerprint"

__all__ = [
    "COGNITIVE_FINGERPRINT_KEY",
    "DEFAULT_HANDOFF_PATH",
    "HANDOFF_VERSION",
    "MAX_DECISIONS",
    "MAX_ERRORS",
    "MAX_GHOSTS",
    "generate_handoff",
    "load_handoff",
    "save_handoff",
]
