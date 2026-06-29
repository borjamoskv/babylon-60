# [C5-REAL] Exergy-Maximized
"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).
"""

from __future__ import annotations

from .detector import EMBEDDING_BOOST_WEIGHT, _embedding_cosine_similarity, detect_contradictions
from .models import ConflictCandidate, ConflictReport
from .scanner import scan_all_contradictions

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "EMBEDDING_BOOST_WEIGHT",
    "_embedding_cosine_similarity",
    "detect_contradictions",
    "scan_all_contradictions",
]
