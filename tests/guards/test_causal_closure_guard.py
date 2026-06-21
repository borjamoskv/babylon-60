# [C5-REAL] Exergy-Maximized
"""Tests for the CausalClosureGuard.

Validates that the pipeline enforces strict thermodynamic causality 
via structural hash verification, rejecting pure prose or empty claims.
"""

import datetime
import pytest

from cortex.guards.causal_closure_guard import CausalClosureGuard, SwarmProposal
from cortex.types.evidence import ClosurePayload, EvidenceBundle, Source


@pytest.fixture
def closure_guard() -> CausalClosureGuard:
    """Provides the causal guard for testing."""
    return CausalClosureGuard()


@pytest.fixture
def valid_evidence() -> EvidenceBundle:
    return EvidenceBundle.forge(
        query="test query",
        sources=[
            Source(uri="test_uri", content_hash="hash123", metadata={"raw": "test data"})
        ],
        retrieved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    )


def test_valid_closure_payload_passes(closure_guard: CausalClosureGuard, valid_evidence: EvidenceBundle) -> None:
    """A structurally sound payload with valid hashes must pass."""
    payload = ClosurePayload.seal(
        claims=[{"cve_id": "CVE-123"}],
        evidence=valid_evidence,
        verdict=True
    )
    assert closure_guard.verify_closure(payload) is True


def test_tampered_payload_hash_fails(closure_guard: CausalClosureGuard, valid_evidence: EvidenceBundle) -> None:
    """If the payload hash is modified after sealing, it must fail."""
    payload = ClosurePayload.seal(
        claims=[{"cve_id": "CVE-123"}],
        evidence=valid_evidence,
        verdict=True
    )
    
    # Tamper the hash to simulate semantic drift
    tampered_payload = ClosurePayload(
        claims=payload.claims,
        evidence=payload.evidence,
        verdict=payload.verdict,
        payload_hash="invalid_hash"
    )
    
    with pytest.raises(RuntimeError, match="Structural payload hash mismatch"):
        closure_guard.verify_closure(tampered_payload)


def test_empty_evidence_and_claims_fails(closure_guard: CausalClosureGuard) -> None:
    """A payload with no claims and no evidence is pure Anergy and must be aborted."""
    empty_evidence = EvidenceBundle.forge(
        query="empty",
        sources=[],
        retrieved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    )
    
    payload = ClosurePayload.seal(
        claims=[],
        evidence=empty_evidence,
        verdict=False
    )
    
    with pytest.raises(RuntimeError, match="Payload contains no observable evidence"):
        closure_guard.verify_closure(payload)


def test_legacy_closure_empty_content_returns_false(closure_guard: CausalClosureGuard) -> None:
    """Empty legacy content should be safely rejected."""
    proposal = SwarmProposal(agent_id="test", mission_statement="test", content="   ")
    assert not closure_guard.verify_legacy_closure(proposal)


def test_legacy_closure_with_ledger_passes(closure_guard: CausalClosureGuard) -> None:
    """A legacy operation that outputs a LedgerPayload achieves causal closure."""
    content = """Emitting to the audit trail:
LedgerPayload: { "tx": 123, "CORTEX-TAINT": "v1" }
"""
    proposal = SwarmProposal(
        agent_id="test", mission_statement="test", content=content, token_cost=5000
    )
    assert closure_guard.verify_legacy_closure(proposal) is True


def test_legacy_closure_without_structure_throws(closure_guard: CausalClosureGuard) -> None:
    """A legacy operation that outputs only prose must be aborted."""
    content = "I have thought deeply. No code is needed."
    proposal = SwarmProposal(
        agent_id="test", mission_statement="test", content=content, token_cost=5000
    )
    with pytest.raises(RuntimeError, match="Legacy Swarm output must contain permanent invariants"):
        closure_guard.verify_legacy_closure(proposal)
