"""Compatibility wrapper for the canonical ADK runner."""

from cortex.extensions.adk.runner import *  # noqa: F401,F403
from cortex.extensions.adk.runner import __all__ as _EXTENSIONS_ALL

__all__ = list(_EXTENSIONS_ALL)
