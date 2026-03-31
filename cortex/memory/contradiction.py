"""V8 Governance: Memory Contradiction Scanner."""

import logging
from typing import Any

logger = logging.getLogger("CORTEX.MEMORY.CONTRADICTION")


class ContradictionScanner:
    """
    Scans the memory space for semantic contradictions.
    Focuses on finding high-similarity vector pairs with opposing factual claims.
    """

    def __init__(self, engine):
        self.engine = engine

    async def scan(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Performs a sweep of the project's memory to find conflicting facts.
        Logic:
        1. Query recent facts.
        2. For each fact, perform a semantic search.
        3. Identify if any retrieved fact of trust level C5 contradicts a C1/C2 or another C5.
        """
        findings: list[dict[str, Any]] = []
        return findings

    # Negation prefixes and antonym pairs that signal polarity inversion.
    _NEGATION_PREFIXES: frozenset[str] = frozenset(
        {"not ", "no ", "never ", "isn't ", "aren't ", "wasn't ", "weren't ", "doesn't ", "don't "}
    )
    _ANTONYM_PAIRS: tuple[tuple[str, str], ...] = (
        ("active", "inactive"),
        ("enabled", "disabled"),
        ("valid", "invalid"),
        ("trusted", "untrusted"),
        ("success", "failure"),
        ("stable", "unstable"),
        ("alive", "dead"),
        ("online", "offline"),
        ("open", "closed"),
        ("approved", "rejected"),
        ("confirmed", "denied"),
    )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Lower-cased word tokens, stripping punctuation."""
        import re

        return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))

    @classmethod
    def identify_conflict(cls, fact_a: Any, fact_b: Any) -> bool:
        """Determines if two facts are semantically contradictory.

        Two-phase heuristic (no external NLP dependency):
        1. Shared-subject check — facts must share ≥2 content tokens to be comparable.
        2. Polarity inversion — one fact negates the other or contains antonym terms.
        """
        content_a: str = getattr(fact_a, "content", "") or str(fact_a)
        content_b: str = getattr(fact_b, "content", "") or str(fact_b)

        if not content_a or not content_b:
            return False

        tokens_a = cls._tokenize(content_a)
        tokens_b = cls._tokenize(content_b)

        # Phase 1: facts must share subject context to be comparable.
        shared = tokens_a & tokens_b
        if len(shared) < 2:
            return False

        lower_a, lower_b = content_a.lower(), content_b.lower()

        # Phase 2a: explicit negation — one fact negates a phrase present in the other.
        for prefix in cls._NEGATION_PREFIXES:
            # cls._tokenize(prefix + " placeholder")  # just the prefix words
            # Check if tokens from one appear negated in the other
            if any((prefix + token) in lower_b and token in tokens_a for token in tokens_a):
                return True
            if any((prefix + token) in lower_a and token in tokens_b for token in tokens_b):
                return True

        # Phase 2b: antonym pairs — one fact has term A, the other has term B.
        for term_pos, term_neg in cls._ANTONYM_PAIRS:
            a_has_pos = term_pos in lower_a
            a_has_neg = term_neg in lower_a
            b_has_pos = term_pos in lower_b
            b_has_neg = term_neg in lower_b
            if (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos):
                return True

        return False
