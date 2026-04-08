"""Compatibility shim for the canonical ADK tools module."""

from __future__ import annotations

import warnings

warnings.warn(
    "cortex.extensions.adk.tools is deprecated; use cortex.adk.tools instead.",
    DeprecationWarning,
    stacklevel=2,
)

from cortex.adk.tools import (
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
