"""CORTEX v6+ — Agent package."""

from cortex.experimental.extensions.agent.degradation import (
    AgentAction,
    AgentCalcificationError,
    AgentDegradedError,
    AgentResult,
    DegradationLevel,
    DegradationReport,
    ModelUnavailableError,
    SchemaIncompatibilityError,
    SovereignAgentError,
    ToolRegistrationError,
    sovereign_execute,
)
from cortex.experimental.extensions.agent.schema import AgentRole, GuardrailConfig, MemoryConfig

__all__ = [
    # schema
    "AgentRole",
    "GuardrailConfig",
    "MemoryConfig",
    # degradation
    "AgentAction",
    "AgentCalcificationError",
    "AgentDegradedError",
    "AgentResult",
    "DegradationLevel",
    "DegradationReport",
    "ModelUnavailableError",
    "SchemaIncompatibilityError",
    "SovereignAgentError",
    "ToolRegistrationError",
    "sovereign_execute",
]
