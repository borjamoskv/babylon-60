"""Thin CLI bootstrap for the CORTEX MCP server."""

from __future__ import annotations

import sys

__all__ = ["main"]


def main() -> None:
    """Start the MCP server or emit a clean dependency error."""
    try:
        from cortex.mcp.server import run_server
    except ImportError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    run_server()
