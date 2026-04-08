"""CORTEX Sovereign Vibe-Coding Composer (Vector 1).

Autonomous JIT frontend synthesis engine reinforcing the Industrial Noir 2026 aesthetic.
"""

from __future__ import annotations

from .app_forge import (
    APP_FORGE_FACT_TYPE,
    APP_FORGE_RUNTIME,
    APP_FORGE_SOURCE,
    AppForgeInvocation,
    AppForgeRuntimeManifest,
    EngineSovereignStateStore,
    InMemorySovereignStateStore,
    SovereignAppForge,
    SovereignPrimitive,
    SovereignStateEnvelope,
    SovereignStateStore,
)
from .engine import ComposerEngine
from .manifesto import COMPOSER_MANIFESTO
from .vision_qa import AestheticAuditor

__all__ = [
    "APP_FORGE_FACT_TYPE",
    "APP_FORGE_RUNTIME",
    "APP_FORGE_SOURCE",
    "AestheticAuditor",
    "AppForgeInvocation",
    "AppForgeRuntimeManifest",
    "COMPOSER_MANIFESTO",
    "ComposerEngine",
    "EngineSovereignStateStore",
    "InMemorySovereignStateStore",
    "SovereignAppForge",
    "SovereignPrimitive",
    "SovereignStateEnvelope",
    "SovereignStateStore",
]
