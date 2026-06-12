"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.
"""

from __future__ import annotations

from .core import detect_contradictions
from .models import ConflictCandidate, ConflictReport
from .batch_scanner import scan_all_contradictions

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
]

# Provide aliases for tests checking internal implementation
from .scoring import (
    _embedding_cosine_similarity,
    EMBEDDING_BOOST_WEIGHT,
)

__all__ += [
    "_embedding_cosine_similarity",
    "EMBEDDING_BOOST_WEIGHT",
]
