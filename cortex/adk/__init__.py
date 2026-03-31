"""Compatibility exports for the legacy ``cortex.adk`` package path."""

from cortex.extensions.adk.runner import main, run_cli, run_web

__all__ = ["main", "run_cli", "run_web"]
