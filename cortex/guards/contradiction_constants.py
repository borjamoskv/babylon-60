# [C5-REAL] Exergy-Maximized
"""Constants and pattern definitions for the contradiction guard."""

from __future__ import annotations

import re

_NOISE_PREFIXES = ("MAILTV-1: ARCHIVE",)
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "en",
        "un",
        "una",
        "y",
        "o",
        "que",
        "con",
        "por",
        "para",
        "se",
        "es",
        "no",
        "al",
        "su",
        "más",
        "como",
        "pero",
        "sin",
        "sobre",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "and",
        "or",
        "not",
        "but",
        "this",
        "that",
        "it",
        "its",
    }
)

_NEGATION_MARKERS = frozenset(
    {
        "no usar",
        "never use",
        "prohibido",
        "eliminado",
        "forbidden",
        "deprecated",
        "removed",
        "replaced",
        "reemplazado",
        "obsolete",
        "no utilizar",
        "don't use",
        "do not use",
        "eliminamos",
        "matado",
        "killed",
        "purged",
        "deleted",
    }
)

_SUPERSESSION_MARKERS = re.compile(
    r"supersed|replac|obsolet|invalidat|deprecat|eliminad|reemplaz|upgrade|migrat|refactor",
    re.IGNORECASE,
)

_VERSION_PATTERN = re.compile(r"\b[vV](\d+(?:\.\d+)*)\b")
