from __future__ import annotations

from pydantic import ValidationError

from cortex.agents.contracts import (
    ApprovalEvent,
    CausalEdgePayload,
    DecisionEdgePayload,
    FactCommitReceipt,
    FactProposal,
    ProvenanceRecord,
    RejectionEnvelope,
    SovereignFact,
    TaskErrorPayload,
    TaskRequestPayload,
    TaskResultPayload,
    ToolEvidencePayload,
)


def test_legacy_task_request_payload_still_validates() -> None:
    payload = TaskRequestPayload(
        task_id="task-1",
        objective="tool:search",
        input={"query": "cortex"},
        constraints={"tenant_id": "alpha"},
    )

    assert payload.task_id == "task-1"
    assert payload.input["query"] == "cortex"


def test_task_result_payload_requires_non_blank_op() -> None:
    payload = TaskResultPayload[dict](op="status", result={"status": "ok"})

    assert payload.ok is True
    assert payload.result["status"] == "ok"

    try:
        TaskResultPayload[dict](op="   ", result={})
    except ValidationError as exc:
        assert "op must not be blank" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for blank op")


def test_task_error_payload_requires_non_blank_error() -> None:
    payload = TaskErrorPayload(error="boom", op="status", supported=["status"])

    assert payload.ok is False
    assert payload.error == "boom"

    try:
        TaskErrorPayload(error="   ")
    except ValidationError as exc:
        assert "error must not be blank" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for blank error")


def test_fact_proposal_syncs_fact_proposal_id() -> None:
    fact = SovereignFact[dict](
        tenant_id="alpha",
        agent_id="agent-1",
        session_id="sess-1",
        payload={"answer": "ok"},
        payload_hash="abc123",
        taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:abc123",
    )

    proposal = FactProposal[dict](fact=fact, rationale="validated output")

    assert proposal.fact.proposal_id == proposal.proposal_id
    assert proposal.fact.status == "proposed"


def test_sovereign_fact_requires_cortex_taint_prefix() -> None:
    try:
        SovereignFact[dict](
            tenant_id="alpha",
            agent_id="agent-1",
            session_id="sess-1",
            payload={"answer": "ok"},
            payload_hash="abc123",
            taint="bad-prefix",
        )
    except ValidationError as exc:
        assert "taint must start with 'taint:'" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for invalid taint")


def test_tool_evidence_ok_requires_output_hash_or_artifact_ref() -> None:
    try:
        ToolEvidencePayload(
            tool_name="search",
            tenant_id="alpha",
            agent_id="agent-1",
            session_id="sess-1",
            input_hash="input-hash",
            taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:input-hash",
            status="ok",
        )
    except ValidationError as exc:
        assert "requires output_hash or artifact_ref" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for incomplete ok evidence")


def test_tool_evidence_error_requires_error_code() -> None:
    try:
        ToolEvidencePayload(
            tool_name="search",
            tenant_id="alpha",
            agent_id="agent-1",
            session_id="sess-1",
            input_hash="input-hash",
            taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:input-hash",
            status="error",
        )
    except ValidationError as exc:
        assert "requires error_code" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for missing error_code")


def test_approved_event_requires_artifact_hash() -> None:
    try:
        ApprovalEvent(
            proposal_id="proposal-1",
            status="approved",
            actor_id="operator-1",
        )
    except ValidationError as exc:
        assert "approved events require artifact_hash" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for incomplete approval")


def test_causal_edge_requires_parent_or_signal() -> None:
    try:
        CausalEdgePayload(
            fact_id="fact-1",
            tenant_id="alpha",
            taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:edge-hash-1",
        )
    except ValidationError as exc:
        assert "causal edges require parent_id or signal_id" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for incomplete causal edge")


def test_decision_edge_and_commit_receipt_capture_core_ids() -> None:
    provenance = ProvenanceRecord(source="tool:web", payload_ref="artifact://1")
    fact = SovereignFact[dict](
        tenant_id="alpha",
        agent_id="agent-1",
        session_id="sess-1",
        payload={"summary": "done"},
        payload_hash="hash-1",
        taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:hash-1",
        provenance=[provenance],
        decision_id="decision-1",
    )

    edge = DecisionEdgePayload(
        decision_id="decision-1",
        fact_id=fact.fact_id,
        tenant_id="alpha",
        taint="taint:agent-1:sess-1:2026-04-04T00:00:00+00:00:decision-edge-hash-1",
    )
    receipt = FactCommitReceipt(
        fact_id=fact.fact_id,
        proposal_id="proposal-1",
        ledger_hash="ledger-hash-1",
    )

    assert edge.edge_type == "used_as_evidence"
    assert receipt.status == "committed"
    assert receipt.fact_id == fact.fact_id


def test_runtime_artifacts_require_cortex_taint_prefix() -> None:
    for factory in (
        lambda: ToolEvidencePayload(
            tool_name="search",
            tenant_id="alpha",
            agent_id="agent-1",
            session_id="sess-1",
            input_hash="input-hash",
            output_hash="output-hash",
            taint="bad-prefix",
            status="ok",
        ),
        lambda: RejectionEnvelope(
            tenant_id="alpha",
            agent_id="agent-1",
            session_id="sess-1",
            project="proj",
            taint="bad-prefix",
            reason="failure",
        ),
        lambda: CausalEdgePayload(
            fact_id="fact-1",
            parent_id="fact-0",
            tenant_id="alpha",
            taint="bad-prefix",
        ),
        lambda: DecisionEdgePayload(
            decision_id="decision-1",
            fact_id="fact-1",
            tenant_id="alpha",
            taint="bad-prefix",
        ),
    ):
        try:
            factory()
        except ValidationError as exc:
            assert "taint must start with 'taint:'" in str(exc)
        else:
            raise AssertionError("Expected ValidationError for invalid taint")
