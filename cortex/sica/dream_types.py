# [C5-REAL] Exergy-Maximized
"""SICA Dream Engine Shared Types."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cortex.sica.object_level import ExecutionStep, StepOutcome
from cortex.sica.strategy import Heuristic


@dataclass
class DreamInsight:
    """A pattern discovered during dream consolidation.

    Each insight is actionable - it can become a heuristic,
    modify a weight, or flag a blind spot.
    """

    insight_type: str  # "rule" | "anti_pattern" | "specialization" | "combo" | "abstraction"
    description: str
    confidence: float  # [0, 1]
    evidence_count: int
    proposed_heuristic: Heuristic | None = None
    proposed_weight_change: dict[str, float] | None = None  # {heuristic_name: delta}
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class DreamReport:
    """Summary of a dream cycle."""

    cycle_id: int
    duration_ms: float
    traces_replayed: int
    fragments_recombined: int
    insights_discovered: list[DreamInsight]
    abstractions_formed: int
    memories_pruned: int


@dataclass
class _TraceFragment:
    steps: list[ExecutionStep]
    source_trace: str
    outcome: StepOutcome


@dataclass
class _Abstraction:
    pattern: str
    success_rate: float
    observations: int

    def update(self, new_rate: float, new_obs: int) -> None:
        # Weighted running average
        total = self.observations + new_obs
        self.success_rate = (self.success_rate * self.observations + new_rate * new_obs) / total
        self.observations = total

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "success_rate": round(self.success_rate, 3),
            "observations": self.observations,
        }
