# [C5-REAL] Exergy-Maximized
"""CORTEX ADK Runner - CLI and Web interface for ADK agents.

Wrapper redirecting to cortex.extensions.adk.runner to eliminate code duplication.
"""

from __future__ import annotations

from cortex.extensions.adk.runner import (
    main,
    run_cli,
    run_web,
)

__all__ = [
    "main",
    "run_cli",
    "run_web",
]
