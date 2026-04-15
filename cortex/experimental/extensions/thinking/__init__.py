"""CORTEX v5.0 — Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from cortex.experimental.extensions.thinking.fusion import (
    FusedThought,
    FusionStrategy,
    ModelResponse,
    ThinkingHistory,
    ThoughtFusion,
)
from cortex.experimental.extensions.thinking.orchestra import ThoughtOrchestra
from cortex.experimental.extensions.thinking.pool import ThinkingRecord
from cortex.experimental.extensions.thinking.presets import OrchestraConfig, ThinkingMode

__all__ = [
    "ThoughtOrchestra",
    "OrchestraConfig",
    "ThinkingMode",
    "ThinkingRecord",
    "ThoughtFusion",
    "FusionStrategy",
    "FusedThought",
    "ModelResponse",
    "ThinkingHistory",
]
