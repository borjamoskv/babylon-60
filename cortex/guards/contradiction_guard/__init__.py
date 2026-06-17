from __future__ import annotations

from cortex.guards.contradiction_guard.detector import (
    detect_contradictions,
)
from cortex.guards.contradiction_guard.models import ConflictCandidate, ConflictReport
from cortex.guards.contradiction_guard.scanner import scan_all_contradictions
from cortex.guards.contradiction_guard.utils import (
    EMBEDDING_BOOST_WEIGHT,
    _embedding_cosine_similarity,
)

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "EMBEDDING_BOOST_WEIGHT",
    "_embedding_cosine_similarity",
]
