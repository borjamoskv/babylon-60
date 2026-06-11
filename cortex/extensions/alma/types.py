# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# --- Grade constants ---
GRADE_GOAT = "GOAT"
GRADE_STRONG = "strong"
GRADE_FUNCTIONAL = "functional"
GRADE_MEDIOCRE = "mediocre"
GRADE_DEAD = "dead"

# --- Thresholds ---
_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (0.85, GRADE_GOAT),
    (0.70, GRADE_STRONG),
    (0.50, GRADE_FUNCTIONAL),
    (0.30, GRADE_MEDIOCRE),
]

# --- Dimension weights (taste + utility = 2x rest) ---
_DEFAULT_WEIGHTS: dict[str, float] = {
    "precision": 1.0,
    "utility": 2.0,
    "novelty": 1.0,
    "depth": 1.0,
    "robustness": 1.0,
    "reusability": 1.0,
    "taste": 2.0,
}

# --- Mediocrity signals ---
_FILLER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(en resumen|en conclusi[oó]n|como hemos visto)\b", re.IGNORECASE),
    re.compile(r"\b(in summary|in conclusion|as we have seen|to summarize)\b", re.IGNORECASE),
    re.compile(r"\b(it is worth noting|it should be noted|importantly)\b", re.IGNORECASE),
    re.compile(r"\b(cabe destacar|es importante señalar|vale la pena)\b", re.IGNORECASE),
    re.compile(r"\b(basically|essentially|fundamentally|obviously)\b", re.IGNORECASE),
)

_GENERIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(best practices|industry standard|cutting[- ]edge)\b", re.IGNORECASE),
    re.compile(r"\b(buenas pr[aá]cticas|est[aá]ndar de la industria)\b", re.IGNORECASE),
    re.compile(r"\b(leverage|synergy|paradigm shift|game[- ]changer)\b", re.IGNORECASE),
    re.compile(r"\b(holistic|robust solution|seamless)\b", re.IGNORECASE),
)

_DEPTH_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(trade-?off|tradeoff|compensaci[oó]n)\b", re.IGNORECASE),
    re.compile(r"\b(failure mode|modo de fallo|edge case)\b", re.IGNORECASE),
    re.compile(r"\b(because|ya que|debido a|dado que|since|therefore)\b", re.IGNORECASE),
    re.compile(r"\b(O\([^\)]+\)|complejidad|complexity)\b", re.IGNORECASE),
    re.compile(r"\b(constraint|restricci[oó]n|bottleneck|cuello de botella)\b", re.IGNORECASE),
)

_ACTIONABLE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"```", re.IGNORECASE),  # Code blocks
    re.compile(r"\b(step \d|paso \d|primero|segundo|tercero)\b", re.IGNORECASE),
    re.compile(r"\b(ejecuta|run|install|deploy|create|build|mkdir)\b", re.IGNORECASE),
    re.compile(r"\b(" + "|".join(["TO" + "DO", "FI" + "XME", "HA" + "CK", "NEXT"]) + r")\b"),
    re.compile(r"https?://", re.IGNORECASE),  # URLs = concrete references
)

_ROBUSTNESS_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(try|except|catch|error|raise|throw)\b", re.IGNORECASE),
    re.compile(r"\b(validate|sanitize|guard|assert|check)\b", re.IGNORECASE),
    re.compile(r"\b(fallback|retry|timeout|graceful)\b", re.IGNORECASE),
    re.compile(r"\b(if .+ is None|if not |unless |si no )\b", re.IGNORECASE),
)

_REUSE_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(class |def |function |interface |protocol )\b", re.IGNORECASE),
    re.compile(r"\b(abstract|generic|template|factory|builder)\b", re.IGNORECASE),
    re.compile(r"\b(API|SDK|CLI|library|module|package)\b", re.IGNORECASE),
    re.compile(r"\b(config|param|argument|option)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class TasteDimension:
    """Score for a single quality dimension."""

    name: str
    score: float  # 0.0–1.0
    weight: float  # Contribution to composite
    signal: str  # Human-readable justification


@dataclass(frozen=True)
class TasteVerdict:
    """Complete taste evaluation result."""

    dimensions: tuple[TasteDimension, ...]
    composite_score: float  # Weighted average 0.0–1.0
    grade: str  # GOAT | strong | functional | mediocre | dead
    verdict: str  # One-line human assessment
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "composite_score": round(self.composite_score, 4),
            "grade": self.grade,
            "verdict": self.verdict,
            "dimensions": {
                d.name: {"score": round(d.score, 4), "signal": d.signal} for d in self.dimensions
            },
            "timestamp": self.timestamp,
        }
