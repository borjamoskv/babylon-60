"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.
"""

from __future__ import annotations

from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from cortex.guards.contradiction_guard.detector import detect_contradictions, scan_all_contradictions
from cortex.guards.contradiction_guard.core import _embedding_cosine_similarity, EMBEDDING_BOOST_WEIGHT

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "_embedding_cosine_similarity",
    "EMBEDDING_BOOST_WEIGHT",
]
