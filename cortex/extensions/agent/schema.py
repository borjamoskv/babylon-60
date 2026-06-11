# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Declarative Agent Schema (YAML → Engine).

Wrapper redirecting to cortex.agents.schema to eliminate code duplication.
"""

from __future__ import annotations

from cortex.agents.schema import AgentRole, GuardrailConfig, MemoryConfig

__all__ = [
    "AgentRole",
    "GuardrailConfig",
    "MemoryConfig",
]
