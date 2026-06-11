# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - YAML Agent Loader (role.yaml → CortexEngine).

Wrapper redirecting to cortex.extensions.agent.loader to eliminate code duplication.
"""

from __future__ import annotations

from cortex.extensions.agent.loader import (
    AgentInstance,
    compile_agent,
    load_agent,
)

__all__ = [
    "AgentInstance",
    "compile_agent",
    "load_agent",
]
