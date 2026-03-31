"""Causality data models — Taint status, confidence ordering, fact nodes.

Tri-state taint (CLEAN/SUSPECT/TAINTED) prevents binary overshoot:
a boolean taint would rupture half the DAG on a mild suspicion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    from cortex.cortex_rs import Confidence, FactNode, TaintStatus
except ImportError:
    # Fallback to Python if Rust extension is missing (pre-compilation state)
    class Confidence(str, Enum):
        C1 = "C1"
        C2 = "C2"
        C3 = "C3"
        C4 = "C4"
        C5 = "C5"

    class TaintStatus(str, Enum):
        CLEAN = "clean"
        SUSPECT = "suspect"
        TAINTED = "tainted"

    @dataclass
    class FactNode:
        fact_id: str
        confidence: Confidence
        effective_confidence: Confidence
        invalidated: bool = False
        taint_status: TaintStatus = TaintStatus.CLEAN
        parents: list[str] = field(default_factory=list)
        children: list[str] = field(default_factory=list)
        source: Optional[str] = None

# Ordinal mapping for confidence arithmetic
# Note: cortex_rs enums start at 0, but we maintain the Python-style mapping for now
CONFIDENCE_ORDER: dict[Confidence, int] = {
    Confidence.C1: 1,
    Confidence.C2: 2,
    Confidence.C3: 3,
    Confidence.C4: 4,
    Confidence.C5: 5,
}

REVERSE_CONFIDENCE_ORDER: dict[int, Confidence] = {v: k for k, v in CONFIDENCE_ORDER.items()}

