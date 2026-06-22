from __future__ import annotations

from cortex.guards.contradiction_guard.batch import scan_all_contradictions
from cortex.guards.contradiction_guard.detector import detect_contradictions
from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from cortex.guards.contradiction_guard.scoring import EMBEDDING_BOOST_WEIGHT
from cortex.guards.contradiction_guard.text_utils import _embedding_cosine_similarity

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "_embedding_cosine_similarity",
    "EMBEDDING_BOOST_WEIGHT",
]
