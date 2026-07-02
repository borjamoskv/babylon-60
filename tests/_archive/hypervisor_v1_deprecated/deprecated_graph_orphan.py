import pytest
import logging
from datetime import datetime, timezone

from babylon60.engine.causal.belief_objects import (
    BeliefObject,
    BeliefState,
    BeliefVerdict,
    VerdictAction,
    ProvenanceEnvelope,
    BeliefRelations
)
from babylon60.extensions.hypervisor.belief_engine import BeliefEngine


class MockFact:
    def __init__(self, content, fact_type, project, meta, confidence):
        self.content = content
        self.fact_type = fact_type
        self.project = project
        self.meta = meta
        self.confidence = confidence


class MockEngine:
    def __init__(self):
        self.facts = []

    async def store(self, content, fact_type, project, source, meta, confidence):
        obj_dict = meta.get("belief_object", {})
        belief_id = obj_dict.get("id") or obj_dict.get("belief_id")

        self.facts = [
            f for f in self.facts if f.meta.get("belief_object", {}).get("belief_id") != belief_id
            and f.meta.get("belief_object", {}).get("id") != belief_id
        ]

        self.facts.append(MockFact(content, fact_type, project, meta, confidence))

    async def recall(self, project, limit=None, tenant_id="default", fact_type=None, offset=0):
        res = [f for f in self.facts if f.fact_type == "belief" and f.project == project]
        if limit:
            return res[:limit]
        return res


def make_mock_provenance(signer="test") -> ProvenanceEnvelope:
    return ProvenanceEnvelope(
        source_hash="hash123",
        source_type="test",
        tenant_id="default",
        signer_id=signer,
        signature="sig123",
        created_at=datetime.now(timezone.utc).isoformat(),
        was_generated_by="test"
    )

@pytest.mark.asyncio
async def test_cascading_quarantine_graph_orphan():
    mock_db = MockEngine()
    engine = BeliefEngine(cortex_engine=mock_db)
    engine._max_context = 1000

    PROJECT = "test_graph"

    root_belief = BeliefObject(
        belief_id="root-1",
        proposition="Axioma: La gravedad es atractiva.",
        semantic_embedding=[],
        state=BeliefState.ACTIVE,
        confidence_score=1.0,
        variance=0.0,
        decay_rate=0.0,
        provenance=make_mock_provenance(),
        relations=BeliefRelations()
    )
    await engine._persist_belief(root_belief)

    total_beliefs = 1
    children_l1 = []

    for i in range(5):
        child = BeliefObject(
            belief_id=f"child-l1-{i}",
            proposition=f"Consecuencia L1 {i}",
            semantic_embedding=[],
            state=BeliefState.ACTIVE,
            confidence_score=0.8,
            variance=0.1,
            decay_rate=0.01,
            provenance=make_mock_provenance(),
            relations=BeliefRelations(entails=[root_belief.belief_id])
        )
        await engine._persist_belief(child)
        children_l1.append(child)
        total_beliefs += 1

    for l1_child in children_l1:
        for j in range(10):
            child = BeliefObject(
                belief_id=f"child-l2-{l1_child.belief_id}-{j}",
                proposition=f"Consecuencia L2 {j}",
                semantic_embedding=[],
                state=BeliefState.ACTIVE,
                confidence_score=0.5,
                variance=0.2,
                decay_rate=0.05,
                provenance=make_mock_provenance(),
                relations=BeliefRelations(entails=[l1_child.belief_id])
            )
            await engine._persist_belief(child)
            total_beliefs += 1

    active_count = sum(1 for f in mock_db.facts if f.meta["belief_object"].get("state", f.meta["belief_object"].get("status")) == "active")
    assert active_count == total_beliefs, f"Expected {total_beliefs} active beliefs, got {active_count}"

    verdict = BeliefVerdict(
        action=VerdictAction.QUARANTINE,
        model="claude-opus-4.6-premium",
        reason="Falsa premisa detectada. Aislamiento requerido.",
    )

    await engine._quarantine_belief(root_belief, verdict)

    active_count_post = sum(1 for f in mock_db.facts if f.meta["belief_object"].get("state", f.meta["belief_object"].get("status")) == "active")
    quarantined_count = sum(1 for f in mock_db.facts if f.meta["belief_object"].get("state", f.meta["belief_object"].get("status")) == "quarantined")

    assert active_count_post == 0, f"Expected 0 active beliefs post-collapse, got {active_count_post}"
    assert quarantined_count == total_beliefs, f"Expected {total_beliefs} quarantined beliefs, got {quarantined_count}"
