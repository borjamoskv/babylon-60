"""CORTEX v5.0 — CLI.

Sovereign Command-Line Interface for CORTEX.
"""

from __future__ import annotations

__all__ = ["cli", "console", "get_engine"]  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str):
    if name == "cli":
        from cortex.cli.main import cli

        return cli
    if name in {"console", "get_engine"}:
        from cortex.cli.common import console, get_engine

        exports = {
            "console": console,
            "get_engine": get_engine,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
