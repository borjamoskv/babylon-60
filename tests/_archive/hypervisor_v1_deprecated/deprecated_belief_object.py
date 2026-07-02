# [C5-REAL] Exergy-Maximized

from __future__ import annotations
import pytest

from babylon60.engine.causal.belief_objects import (
    BeliefState,
    BeliefVerdict,
    VerdictAction,
    BeliefObject,
    ProvenanceEnvelope,
    BeliefRelations
)

class TestBeliefStatus:
    def test_lifecycle_states(self):
        assert BeliefState.ACTIVE.value == "active"
        assert BeliefState.QUARANTINED.value == "quarantined"
        assert BeliefState.DISCARDED.value == "discarded"
        assert BeliefState.CONTESTED.value == "contested"
        assert BeliefState.SUBSUMED.value == "subsumed"
        assert BeliefState.ORPHANED.value == "orphaned"

class TestProvenanceEnvelope:
    def test_valid_fields(self):
        env = ProvenanceEnvelope(
            source_hash="hash1",
            source_type="fact",
            tenant_id="t1",
            signer_id="s1",
            signature="sig1",
            created_at="2026-03-14T00:00:00Z",
            was_generated_by="agent"
        )
        assert env.source_type == "fact"

class TestBeliefObject:
    def test_creation_defaults(self):
        env = ProvenanceEnvelope(
            source_hash="hash1",
            source_type="fact",
            tenant_id="t1",
            signer_id="s1",
            signature="sig1",
            created_at="2026-03-14T00:00:00Z",
            was_generated_by="agent"
        )
        belief = BeliefObject(
            belief_id="b-1",
            proposition="The launch is Q2 2026",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.4,
            variance=0.1,
            decay_rate=0.01,
            provenance=env,
            relations=BeliefRelations()
        )
        assert belief.confidence_score == 0.4
        assert belief.state == BeliefState.ACTIVE
        assert belief.relations.discards == []
        assert belief.relations.entails == []

    def test_serialization_roundtrip(self):
        env = ProvenanceEnvelope(
            source_hash="hash1",
            source_type="fact",
            tenant_id="t1",
            signer_id="s1",
            signature="sig1",
            created_at="2026-03-14T00:00:00Z",
            was_generated_by="agent"
        )
        belief = BeliefObject(
            belief_id="b-1",
            proposition="SQLite is the persistence layer",
            semantic_embedding=[0.1, 0.2, 0.3],
            state=BeliefState.ACTIVE,
            confidence_score=0.8,
            variance=0.0,
            decay_rate=0.0,
            provenance=env,
            relations=BeliefRelations(entails=["fact-99", "fact-100"], discards=["belief-old-1"])
        )

        data = belief.model_dump()
        restored = BeliefObject.model_validate(data)

        assert restored.proposition == belief.proposition
        assert restored.confidence_score == belief.confidence_score
        assert restored.relations.discards == ["belief-old-1"]
        assert restored.relations.entails == ["fact-99", "fact-100"]
        assert restored.provenance.signer_id == "s1"

class TestBeliefVerdict:
    def test_accept_verdict(self):
        verdict = BeliefVerdict(
            action=VerdictAction.ACCEPT,
            model="deep_think",
        )
        assert verdict.action == VerdictAction.ACCEPT
        assert verdict.contradictions == ()
        assert verdict.cost_tokens == 0

    def test_quarantine_verdict(self):
        verdict = BeliefVerdict(
            action=VerdictAction.QUARANTINE,
            model="opus",
            contradictions=("b-1", "b-2"),
            reason="Belief contradicts axiomatic B-1 and B-2",
        )
        assert verdict.action == VerdictAction.QUARANTINE
        assert len(verdict.contradictions) == 2
