# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import pytest

from babylon60.memory.scheduler import MemoryScheduler, SchedulerConfig
from babylon60.engine.causal.belief_objects import BeliefObject, BeliefState, ProvenanceEnvelope, BeliefRelations


@dataclass
class MockBelief:
    proposition: str
    content: str = ""
    belief_id: str | None = None
    id: str | None = None
    confidence_score: float = 0.5
    timestamp_last_verified: float | None = None
    cost_tokens: float | None = None
    contamination_risk: float = 0.0
    state: str = "active"
    status: str = "active"

    def is_quarantined(self) -> bool:
        return self.state == "quarantined" or self.status == "quarantined"


def test_scheduler_config_defaults() -> None:
    config = SchedulerConfig()
    assert config.w_relevance == 0.5
    assert config.w_confidence == 0.3
    assert config.w_recency == 0.2
    assert config.contamination_threshold == 0.7
    assert config.recency_decay_rate == 1e-6


def test_score_equation_with_mock_belief() -> None:
    config = SchedulerConfig(
        w_relevance=0.4,
        w_confidence=0.3,
        w_recency=0.3,
        contamination_threshold=0.8,
        recency_decay_rate=1e-5,
    )
    scheduler = MemoryScheduler(config)

    belief = MockBelief(
        proposition="Testing content scheduling",
        confidence_score=1.0,
        timestamp_last_verified=time.time(),
        cost_tokens=10.0,
        contamination_risk=0.1,
    )

    score = scheduler.score(belief, relevance=1.0, contamination_risk=0.1)
    assert score == pytest.approx(1.0 / 10.1)


def test_score_relevance_graceful_fallback() -> None:
    scheduler = MemoryScheduler()
    belief = MockBelief(
        proposition="Test content",
        confidence_score=0.8,
        cost_tokens=5.0,
    )

    score_q1 = scheduler.score(belief, query="query1")
    score_q2 = scheduler.score(belief, query="query2")
    assert score_q1 != score_q2


def test_confidence_resolution() -> None:
    scheduler = MemoryScheduler()
    b_float = MockBelief(proposition="Test", confidence_score=0.7)
    assert scheduler._extract_confidence_value(b_float) == 0.7


def test_recency_exponential_decay() -> None:
    from unittest.mock import patch
    config = SchedulerConfig(recency_decay_rate=0.1)
    scheduler = MemoryScheduler(config)

    now = 1700000000.0
    with patch("time.time", return_value=now):
        b_fresh = MockBelief(proposition="Test", timestamp_last_verified=now)
        b_old = MockBelief(proposition="Test", timestamp_last_verified=now - 10.0)

        rec_fresh = scheduler._calculate_recency(b_fresh)
        rec_old = scheduler._calculate_recency(b_old)

        assert rec_fresh == pytest.approx(1.0, abs=1e-3)
        assert rec_old == pytest.approx(math.exp(-1.0), abs=1e-3)


def test_timestamp_parsing() -> None:
    scheduler = MemoryScheduler()
    assert scheduler._parse_timestamp(123456789.0) == 123456789.0

    iso_str = "2026-06-30T00:00:00Z"
    expected = datetime.fromisoformat("2026-06-30T00:00:00+00:00").timestamp()
    assert scheduler._parse_timestamp(iso_str) == expected


def test_admit_logic() -> None:
    scheduler = MemoryScheduler(SchedulerConfig(contamination_threshold=0.6))
    b_ok = MockBelief(proposition="Ok", contamination_risk=0.3)
    assert scheduler.admit(b_ok) is True

    b_high_risk = MockBelief(proposition="Risk", contamination_risk=0.8)
    assert scheduler.admit(b_high_risk) is False

    b_quarantined = MockBelief(proposition="Quarantined", state="quarantined")
    assert scheduler.admit(b_quarantined) is False


def test_rank_beliefs_with_budget() -> None:
    scheduler = MemoryScheduler()

    b1 = MockBelief(proposition="Small", cost_tokens=2.0, confidence_score=1.0)
    b2 = MockBelief(proposition="Medium", cost_tokens=5.0, confidence_score=0.8)
    b3 = MockBelief(proposition="Large", cost_tokens=10.0, confidence_score=0.6)

    beliefs = [b3, b1, b2]
    ranked_no_budget = scheduler.rank_beliefs(beliefs, query="test")
    assert len(ranked_no_budget) == 3
    assert ranked_no_budget[0] == b1
    assert ranked_no_budget[1] == b2
    assert ranked_no_budget[2] == b3

    ranked_budget = scheduler.rank_beliefs(beliefs, query="test", token_budget=8)
    assert len(ranked_budget) == 2
    assert ranked_budget[0] == b1
    assert ranked_budget[1] == b2


def test_real_belief_object_integration() -> None:
    scheduler = MemoryScheduler()

    belief = BeliefObject(
        belief_id="b-test-1",
        proposition="Sovereign memory scheduling is functional",
        semantic_embedding=[],
        state=BeliefState.ACTIVE,
        confidence_score=0.8,
        variance=0.1,
        decay_rate=0.01,
        provenance=ProvenanceEnvelope(
            source_hash="h",
            source_type="test",
            tenant_id="t",
            signer_id="s",
            signature="s",
            created_at="2026-06-30T00:00:00Z",
            was_generated_by="test"
        ),
        relations=BeliefRelations()
    )

    score = scheduler.score(belief, query="scheduler")
    assert score > 0.0
    assert scheduler.admit(belief) is True
