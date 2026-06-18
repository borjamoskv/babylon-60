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

from cortex.audit.cognitive_router.classifier import SafetyClassifier
from cortex.audit.cognitive_router.debugger import RoutingReplayDebugger
from cortex.audit.cognitive_router.models import RoutingDecision, cosine_similarity
from cortex.audit.cognitive_router.router import CognitiveRouter
from cortex.audit.cognitive_router.simulator import AdversarialPromptSimulator

__all__ = [
    "SafetyClassifier",
    "RoutingReplayDebugger",
    "RoutingDecision",
    "cosine_similarity",
    "CognitiveRouter",
    "AdversarialPromptSimulator",
]
