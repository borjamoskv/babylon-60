# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX Memory Scheduler.

Implements the context scheduling tensor equation from Whitepaper §10:
Score(m) = (Rel·w_r + Conf·w_c + Rec·w_t) / (Cost_tokens + Risk_contam)
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Import from babylon60 extensions
try:
    from babylon60.engine.causal.belief_objects import BeliefObject
except ImportError:
    class BeliefObject:  # type: ignore
        pass

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    """Configuration weights and thresholds for the memory scheduler."""
    w_relevance: float = 0.5
    w_confidence: float = 0.3
    w_recency: float = 0.2
    contamination_threshold: float = 0.7
    recency_decay_rate: float = 1e-6


class MemoryScheduler:
    """Memory scheduler implementing the tensor equation in Whitepaper §10."""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()

    def score(
        self,
        belief: Any,
        query: str | None = None,
        relevance: float | None = None,
        contamination_risk: float | None = None,
    ) -> float:
        if relevance is None:
            relevance = self._calculate_fallback_relevance(belief, query)
        else:
            relevance = max(0.0, min(1.0, relevance))

        confidence = self._extract_confidence_value(belief)
        recency = self._calculate_recency(belief)
        cost_tokens = self._extract_token_cost(belief)

        if contamination_risk is None:
            contamination_risk = float(getattr(belief, "contamination_risk", 0.0))
        else:
            contamination_risk = max(0.0, min(1.0, contamination_risk))

        numerator = (
            (relevance * self.config.w_relevance)
            + (confidence * self.config.w_confidence)
            + (recency * self.config.w_recency)
        )
        denominator = cost_tokens + contamination_risk

        if denominator <= 0:
            denominator = 1e-6

        return numerator / denominator

    def admit(self, belief: Any, contamination_risk: float | None = None) -> bool:
        # Fast path rejection for quarantined/contested beliefs
        state = getattr(belief, "state", None)
        if state is not None:
            state_str = str(getattr(state, "value", state)).lower()
            if state_str in ("quarantined", "contested"):
                return False

        if contamination_risk is None:
            contamination_risk = float(getattr(belief, "contamination_risk", 0.0))

        return contamination_risk <= self.config.contamination_threshold

    def rank_beliefs(
        self,
        beliefs: list[Any],
        query: str | None = None,
        token_budget: int | None = None,
    ) -> list[Any]:
        scored: list[tuple[float, Any]] = []
        for belief in beliefs:
            if not self.admit(belief):
                continue
            score_val = self.score(belief, query=query)
            scored.append((score_val, belief))

        scored.sort(key=lambda x: x[0], reverse=True)

        ranked: list[Any] = []
        cumulative_tokens = 0.0

        for _, belief in scored:
            cost = self._extract_token_cost(belief)
            if token_budget is not None:
                if cumulative_tokens + cost > token_budget:
                    continue
            ranked.append(belief)
            cumulative_tokens += cost

        return ranked

    def _calculate_fallback_relevance(self, belief: Any, query: str | None) -> float:
        prop_key = getattr(belief, "proposition", getattr(belief, "content", ""))
        prop_str = str(prop_key)
        query_str = query or ""

        combined = f"{query_str}:{prop_str}"
        h = hashlib.sha256(combined.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big") / (2**64 - 1)

    def _extract_confidence_value(self, belief: Any) -> float:
        conf_val = getattr(belief, "confidence_score", getattr(belief, "confidence", 0.5))
        if isinstance(conf_val, (int, float)):
            return float(conf_val)
        return 0.5

    def _calculate_recency(self, belief: Any) -> float:
        last_verified = self._resolve_last_verified_timestamp(belief)
        now = time.time()
        delta_t = max(0.0, now - last_verified)
        return math.exp(-self.config.recency_decay_rate * delta_t)

    def _resolve_last_verified_timestamp(self, belief: Any) -> float:
        for attr in (
            "timestamp_last_verified",
            "revised_at",
            "created_at",
            "latest_timestamp",
            "timestamp_created",
        ):
            val = getattr(belief, attr, None)
            parsed = self._parse_timestamp(val)
            if parsed is not None:
                return parsed

        return time.time()

    def _parse_timestamp(self, val: Any) -> float | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                normalized = val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(normalized)
                return dt.timestamp()
            except ValueError:
                pass
        return None

    def _extract_token_cost(self, belief: Any) -> float:
        cost = getattr(belief, "cost_tokens", None)
        if isinstance(cost, (int, float)):
            return float(cost)

        content = getattr(belief, "proposition", getattr(belief, "content", ""))
        return max(1.0, len(str(content)) / 4.0)
