# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-ROUTER: Models and utility functions.
"""

from __future__ import annotations

from dataclasses import dataclass


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


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two vector embeddings."""
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)
