from __future__ import annotations

from .batch import scan_all_contradictions
from .detector import detect_contradictions
from .models import ConflictCandidate, ConflictReport
from .scoring import EMBEDDING_BOOST_WEIGHT, _embedding_cosine_similarity

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "EMBEDDING_BOOST_WEIGHT",
    "_embedding_cosine_similarity",
]
