# [C5-REAL] Exergy-Maximized
"""CORTEX ADK Tools - Bridge between ADK agents and CortexEngine.

Wrapper redirecting to cortex.extensions.adk.tools to eliminate code duplication.
"""

from __future__ import annotations

from cortex.extensions.adk.tools import (
    ALL_TOOLS,
    adk_deprecate,
    adk_ledger_verify,
    adk_search,
    adk_status,
    adk_store,
)

__all__ = [
    "ALL_TOOLS",
    "adk_deprecate",
    "adk_ledger_verify",
    "adk_search",
    "adk_status",
    "adk_store",
]
