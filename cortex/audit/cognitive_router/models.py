# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-ROUTER: AI Cognitive Router Engine (Fable/Mythos State Machine).

Production-grade verifiable routing state machine featuring:
- Declarative policy DSL (YAML/JSON routing language).
- Deterministic classifier pipeline with hybrid keyword + semantic similarity matching.
- Replay debugger engine explaining matching rules and category triggers.
- Adversarial bypass simulator for stress testing classification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.audit.cognitive_router")

_CREATE_ROUTER_LOG_SQL = """
CREATE TABLE IF NOT EXISTS cognitive_router_log (
    routing_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    detected_sensitivity TEXT NOT NULL,
    user_tier TEXT NOT NULL,
    assigned_model TEXT NOT NULL,
    data_retention_flag INTEGER NOT NULL,
    prev_hash TEXT NOT NULL UNIQUE,
    signature TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    routing_policy_version TEXT NOT NULL
);
"""


@dataclass
class RoutingDecision:
    routing_id: str
    timestamp: str
    assigned_model: str
    sensitivity: list[str]
    retention_required: bool
    signature: str
    classifier_version: str
    routing_policy_version: str
