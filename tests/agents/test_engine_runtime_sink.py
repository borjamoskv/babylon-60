from __future__ import annotations

import hashlib
from typing import Any

import pytest

from cortex.agents.contracts import (
    CausalEdgePayload,
    DecisionEdgePayload,
    FactProposal,
    ProvenanceRecord,
    RejectionEnvelope,
    SovereignFact,
    ToolEvidencePayload,
)
from cortex.agents.engine_runtime_sink import EngineRuntimeSink
from cortex.utils.canonical import canonical_json


class RecordingEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def store(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return len(self.calls)


def _taint_from_artifact(agent_id: str, session_id: str, artifact: dict[str, Any]) -> str:
    digest = hashlib.sha3_256(canonical_json(artifact).encode("utf-8")).hexdigest()
    return f"taint:{agent_id}:{session_id}:2026-04-04T00:00:00+00:00:{digest}"


def _proposal() -> FactProposal[dict]:
    fact = SovereignFact[dict](
        tenant_id="tenant-a",
        agent_id="agent-1",
        session_id="sess-1",
        project="proj-a",
        fact_type="agent_step",
        payload={"event": "after_step", "status": "ok"},
        payload_hash="payload-hash-1",
        taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:payload-hash-1",
        provenance=[ProvenanceRecord(source="agent:agent-1")],
    )
    return FactProposal[dict](fact=fact, rationale="runtime observation")


def _tool_evidence(status: str = "ok") -> ToolEvidencePayload:
    return ToolEvidencePayload(
        tool_name="search",
        tenant_id="tenant-a",
        agent_id="agent-1",
        session_id="sess-1",
        project="proj-a",
        input_hash="input-hash-1",
        output_hash="output-hash-1" if status == "ok" else None,
        artifact_ref="artifact://search/1" if status == "ok" else None,
        status=status,
        error_code="tool_failed" if status == "error" else None,
        provenance=ProvenanceRecord(source="agent:agent-1", tool_name="search"),
        taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:input-hash-1",
        arguments={"query": "cortex"},
        normalized_arguments={"query": "cortex"},
    )


@pytest.mark.asyncio
async def test_engine_runtime_sink_persists_fact_proposals_via_allowed_fact_type() -> None:
    engine = RecordingEngine()
    sink = EngineRuntimeSink(engine)

    proposal = _proposal()
    await sink.persist_fact_proposal(proposal)

    call = engine.calls[0]
    assert call["project"] == "proj-a"
    assert call["tenant_id"] == "tenant-a"
    assert call["fact_type"] == "idea"
    assert call["confidence"] == "inferred"
    assert call["source"] == "agent:agent-1"
    assert "proposal" in call["tags"]
    assert call["meta"]["runtime_artifact_kind"] == "fact_proposal"
    assert call["meta"]["runtime_original_fact_type"] == "agent_step"
    assert call["meta"]["runtime_artifact"]["proposal_id"] == proposal.proposal_id
    assert call["meta"]["taint"] == proposal.fact.taint
    assert call["meta"]["runtime_artifact_hash"]


@pytest.mark.asyncio
async def test_engine_runtime_sink_persists_tool_evidence_as_knowledge() -> None:
    engine = RecordingEngine()
    sink = EngineRuntimeSink(engine)

    evidence = _tool_evidence()
    await sink.persist_tool_evidence(evidence)

    call = engine.calls[0]
    assert call["fact_type"] == "knowledge"
    assert call["confidence"] == "verified"
    assert call["source"] == "tool:search"
    assert "tool-evidence" in call["tags"]
    assert call["meta"]["runtime_artifact_kind"] == "tool_evidence"
    assert call["meta"]["runtime_input_hash"] == "input-hash-1"
    assert call["meta"]["runtime_output_hash"] == "output-hash-1"
    assert call["meta"]["taint"] == evidence.taint
    assert call["meta"]["runtime_artifact_hash"]


@pytest.mark.asyncio
async def test_engine_runtime_sink_persists_rejections_as_decisions() -> None:
    engine = RecordingEngine()
    sink = EngineRuntimeSink(engine)

    rejection = RejectionEnvelope(
        tenant_id="tenant-a",
        agent_id="agent-1",
        session_id="sess-1",
        project="proj-a",
        correlation_id="corr-1",
        taint=_taint_from_artifact(
            "agent-1",
            "sess-1",
            {
                "proposal_id": None,
                "fact_id": None,
                "tenant_id": "tenant-a",
                "agent_id": "agent-1",
                "session_id": "sess-1",
                "project": "proj-a",
                "correlation_id": "corr-1",
                "code": "runtime_retry",
                "reason": "tool timed out",
                "retryable": True,
                "failed_stage": "runtime",
                "reasons": [],
            },
        ),
        code="runtime_retry",
        reason="tool timed out",
        retryable=True,
        failed_stage="runtime",
    )
    await sink.persist_rejection(rejection)

    call = engine.calls[0]
    assert call["fact_type"] == "decision"
    assert call["source"] == "agent:agent-1"
    assert "rejection" in call["tags"]
    assert call["meta"]["decision_type"] == "rejection"
    assert call["meta"]["runtime_failed_stage"] == "runtime"
    assert call["meta"]["runtime_artifact"]["reason"] == "tool timed out"
    assert call["meta"]["taint"] == rejection.taint
    assert call["meta"]["runtime_artifact_hash"]


@pytest.mark.asyncio
async def test_engine_runtime_sink_persists_edge_artifacts() -> None:
    engine = RecordingEngine()
    sink = EngineRuntimeSink(engine)

    decision_edge = DecisionEdgePayload(
        decision_id="decision-1",
        fact_id="fact-1",
        tenant_id="tenant-a",
        project="proj-a",
        taint=_taint_from_artifact(
            "agent-1",
            "sess-1",
            {
                "edge_id": "decision-edge-1",
                "decision_id": "decision-1",
                "fact_id": "fact-1",
                "edge_type": "used_as_evidence",
                "tenant_id": "tenant-a",
                "project": "proj-a",
                "correlation_id": None,
                "metadata": {},
            },
        ),
        edge_id="decision-edge-1",
    )
    causal_edge = CausalEdgePayload(
        edge_id="causal-edge-1",
        fact_id="fact-2",
        parent_id="fact-1",
        tenant_id="tenant-a",
        project="proj-a",
        taint=_taint_from_artifact(
            "agent-1",
            "sess-1",
            {
                "edge_id": "causal-edge-1",
                "fact_id": "fact-2",
                "parent_id": "fact-1",
                "signal_id": None,
                "edge_type": "derived_from",
                "tenant_id": "tenant-a",
                "project": "proj-a",
                "metadata": {},
            },
        ),
    )

    await sink.persist_decision_edge(decision_edge)
    await sink.persist_causal_edge(causal_edge)

    decision_call, causal_call = engine.calls
    assert decision_call["fact_type"] == "decision"
    assert decision_call["meta"]["runtime_artifact_kind"] == "decision_edge"
    assert decision_call["meta"]["taint"] == decision_edge.taint
    assert decision_call["meta"]["runtime_artifact_hash"]
    assert causal_call["fact_type"] == "knowledge"
    assert causal_call["meta"]["runtime_artifact_kind"] == "causal_edge"
    assert causal_call["meta"]["taint"] == causal_edge.taint
    assert causal_call["meta"]["runtime_artifact_hash"]
