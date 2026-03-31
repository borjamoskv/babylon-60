"""Compatibility shim for the legacy ``cortex.adk.runner`` entry point."""

from cortex.extensions.adk.runner import main, run_cli, run_web

__all__ = ["main", "run_cli", "run_web"]
