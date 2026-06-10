"""
CORTEX - Contradiction Guard (Axiom 20: Epistemic Consistency).

Every new decision must explicitly invalidate its predecessors or confirm
compatibility. This guard runs at store-time and returns potential
conflicts so the agent can disambiguate before persisting.

Strategy (4-layer, O(N) bounded):
  1. FTS5 keyword overlap - fast, coarse.
  2. Project+topic co-occurrence - medium precision.
  3. Negation / supersession detection - high precision.
  4. Embedding cosine similarity - semantic precision (graceful degradation).

Returns a ConflictReport with scored candidates.
"""

from __future__ import annotations

from .batch import (
    _build_token_index,
    _compare_decisions,
    _prepare_decisions,
    _process_token_bucket,
    scan_all_contradictions,
)
from .constants import (
    _NEGATION_MARKERS,
    _NOISE_PREFIXES,
    _STOP_WORDS,
    _SUPERSESSION_MARKERS,
    _VERSION_PATTERN,
    EMBEDDING_BOOST_WEIGHT,
    MAX_CANDIDATES,
    MIN_OVERLAP_SCORE,
)
from .detector import (
    _fetch_decision_rows,
    _score_candidate,
    detect_contradictions,
)
from .models import ConflictCandidate, ConflictReport
from .utils import (
    _classify_conflict,
    _decrypt_content,
    _detect_negation,
    _detect_supersession,
    _embedding_cosine_similarity,
    _extract_versions,
    _is_noise,
    _jaccard,
    _tokenize,
)

__all__ = [
    "ConflictCandidate",
    "ConflictReport",
    "detect_contradictions",
    "scan_all_contradictions",
    "MAX_CANDIDATES",
    "MIN_OVERLAP_SCORE",
    "EMBEDDING_BOOST_WEIGHT",
    "_NOISE_PREFIXES",
    "_STOP_WORDS",
    "_NEGATION_MARKERS",
    "_SUPERSESSION_MARKERS",
    "_VERSION_PATTERN",
    "_embedding_cosine_similarity",
    "_tokenize",
    "_jaccard",
    "_detect_negation",
    "_detect_supersession",
    "_extract_versions",
    "_is_noise",
    "_decrypt_content",
    "_classify_conflict",
    "_score_candidate",
    "_fetch_decision_rows",
    "_process_token_bucket",
    "_compare_decisions",
    "_prepare_decisions",
    "_build_token_index",
]
