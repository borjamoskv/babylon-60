# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefState,
    VerdictAction,
    ProvenanceEnvelope,
    BeliefRelations
)
from babylon60.extensions.llm._models import IntentProfile
from babylon60.extensions.llm.cognitive_handoff import CognitiveHandoff

class TestCognitiveIntents:
    def test_belief_audit_exists(self):
        assert IntentProfile.BELIEF_AUDIT.value == "belief_audit"

    def test_episodic_processing_exists(self):
        assert IntentProfile.EPISODIC_PROCESSING.value == "episodic_processing"

    def test_original_intents_preserved(self):
        assert IntentProfile.CODE.value == "code"
        assert IntentProfile.REASONING.value == "reasoning"
        assert IntentProfile.CREATIVE.value == "creative"
        assert IntentProfile.ARCHITECT.value == "architect"
        assert IntentProfile.GENERAL.value == "general"

def make_mock_provenance() -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        source_hash="h",
        source_type="test",
        tenant_id="t",
        signer_id="s",
        signature="sig",
        created_at=datetime.now(timezone.utc).isoformat(),
        was_generated_by="test"
    )

class TestCognitiveHandoffNoRouter:
    def _make_handoff(self) -> CognitiveHandoff:
        return CognitiveHandoff(router=None)

    @pytest.mark.asyncio
    async def test_low_confidence_belief_skipped(self):
        handoff = self._make_handoff()
        belief = BeliefObject(
            belief_id="b-1",
            proposition="Maybe the sky is green",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.1,
            variance=0.5,
            decay_rate=0.1,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        verdict = await handoff.process_belief(belief)
        assert verdict.action == VerdictAction.SKIP

    @pytest.mark.asyncio
    async def test_medium_confidence_belief_accepted(self):
        handoff = self._make_handoff()
        belief = BeliefObject(
            belief_id="b-2",
            proposition="SQLite is suitable for local persistence",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.4,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        verdict = await handoff.process_belief(belief)
        assert verdict.action == VerdictAction.ACCEPT

    @pytest.mark.asyncio
    async def test_axiomatic_context_no_escalation_without_router(self):
        handoff = self._make_handoff()
        belief = BeliefObject(
            belief_id="b-3",
            proposition="New claim about entropy",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.6,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        axiomatic_ctx = BeliefObject(
            belief_id="b-4",
            proposition="Entropy always increases",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=1.0,
            variance=0.0,
            decay_rate=0.0,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        verdict = await handoff.process_belief(belief, [axiomatic_ctx])
        assert verdict.action == VerdictAction.ACCEPT

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        handoff = self._make_handoff()
        assert handoff.stats["total_tokens"] == 0
        assert handoff.stats["escalation_count"] == 0
        assert handoff.stats["quarantine_count"] == 0

class TestCognitiveHandoffInvariants:
    def test_involves_axiomatics_true(self):
        axiomatic = BeliefObject(
            belief_id="b-1",
            proposition="Fundamental truth",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=1.0,
            variance=0.0,
            decay_rate=0.0,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        normal = BeliefObject(
            belief_id="b-2",
            proposition="Regular claim",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.6,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        assert CognitiveHandoff._involves_axiomatics(normal, [axiomatic]) is True

    def test_involves_axiomatics_false(self):
        beliefs = [
            BeliefObject(
                belief_id=f"b-{i}",
                proposition=f"claim {i}",
                semantic_embedding=[],
                state=BeliefState.ACTIVE,
                confidence_score=0.6,
                variance=0.1,
                decay_rate=0.01,
                provenance=make_mock_provenance(),
                relations=BeliefRelations()
            ) for i in range(3)
        ]
        candidate = BeliefObject(
            belief_id="b-candidate",
            proposition="candidate",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.5,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        assert CognitiveHandoff._involves_axiomatics(candidate, beliefs) is False

    def test_format_belief_for_prompt(self):
        belief = BeliefObject(
            belief_id="b-1",
            proposition="The API uses gRPC",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.6,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations()
        )
        context = [
            BeliefObject(
                belief_id="b-2",
                proposition="The API uses REST",
                semantic_embedding=[],
                state=BeliefState.ACTIVE,
                confidence_score=0.8,
                variance=0.0,
                decay_rate=0.0,
                provenance=make_mock_provenance(),
                relations=BeliefRelations()
            ),
        ]
        prompt = CognitiveHandoff._format_belief_for_prompt(belief, context)
        assert "The API uses gRPC" in prompt
        assert "The API uses REST" in prompt
        assert "0.6" in prompt
        assert "0.8" in prompt

    def test_default_providers(self):
        handoff = CognitiveHandoff(router=None)
        assert handoff._architect == "anthropic"
        assert handoff._auditor_premium == "anthropic"
        assert handoff._auditor_economic == "z_ai"
        assert handoff._infra == "gemini"
