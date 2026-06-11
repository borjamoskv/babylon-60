# [C5-REAL] Exergy-Maximized
"""Google One Tools - Integration for CORTEX ADK agents.

Wrapper redirecting to cortex.extensions.adk.goog_tools to eliminate code duplication.
"""

from __future__ import annotations

from cortex.extensions.adk.goog_tools import (
    GOOGLE_ONE_TOOLS,
    goog_backup_cortex,
    goog_quota,
    goog_sync_notebooklm,
)

__all__ = [
    "GOOGLE_ONE_TOOLS",
    "goog_backup_cortex",
    "goog_quota",
    "goog_sync_notebooklm",
]
