# [C5-REAL] Exergy-Maximized
"""
Verification: ATMS and SMT Ledger Integrity.
"""

import pytest

from cortex.memory.epistemic_ontology import BeliefObject, BeliefState, ProvenanceEnvelope
from cortex.memory.smt_ledger import BeliefLedger


def test_atms_state_transition_preserves_immutability():
    """Verify that ATMS state transitions do not mutate the original object."""
    envelope = ProvenanceEnvelope(
        source_hash="abcd",
        source_type="agent",
        tenant_id="tenant-1",
        signer_id="agent-0",
        signature="sig0"
    )
    
    belief = BeliefObject(
        proposition_key="sky_is_blue",
        payload={"color": "blue"},
        confidence_score=0.9,
        provenance=envelope
    )
    
    assert belief.state == BeliefState.ACTIVE
    
    # Transition
    new_belief = belief.transition_state(
        new_state=BeliefState.CONTESTED,
        signer_id="agent-1",
        signature="sig1"
    )
    
    # Original remains ACTIVE
    assert belief.state == BeliefState.ACTIVE
    assert belief.provenance.signer_id == "agent-0"
    
    # New belief is CONTESTED
    assert new_belief.state == BeliefState.CONTESTED
    assert new_belief.provenance.signer_id == "agent-1"
    assert new_belief.id == belief.id


def test_lww_violation_hard_fault():
    """Verify that Last-Writer-Wins direct overwrites cause a Hard Fault."""
    ledger = BeliefLedger()
    
    envelope = ProvenanceEnvelope(
        source_hash="abcd",
        source_type="agent",
        tenant_id="tenant-1",
        signer_id="agent-0",
        signature="sig0"
    )
    
    belief = BeliefObject(
        id="static-id",
        proposition_key="sky_is_blue",
        payload={"color": "blue"},
        confidence_score=0.9,
        provenance=envelope
    )
    
    ledger.propose_belief(belief)
    
    # Try to overwrite with a new belief object using the same ID (LWW attempt)
    imposter_belief = BeliefObject(
        id="static-id",
        proposition_key="sky_is_blue",
        payload={"color": "red"},
        confidence_score=0.9,
        provenance=envelope
    )
    
    with pytest.raises(ValueError, match="LWW Violation"):
        ledger.propose_belief(imposter_belief)


def test_ledger_lineage_resolution():
    """Verify that the ledger correctly tracks the history of signed patches."""
    ledger = BeliefLedger()
    
    envelope = ProvenanceEnvelope(
        source_hash="abcd",
        source_type="agent",
        tenant_id="tenant-1",
        signer_id="agent-0",
        signature="sig0"
    )
    
    belief = BeliefObject(
        id="dynamic-id",
        proposition_key="sky_is_blue",
        payload={"color": "blue"},
        confidence_score=0.9,
        provenance=envelope
    )
    
    ledger.propose_belief(belief)
    
    # Patch it
    ledger.patch_belief("dynamic-id", BeliefState.CONTESTED, "agent-1", "sig1")
    ledger.patch_belief("dynamic-id", BeliefState.SUBSUMED, "agent-2", "sig2")
    
    history = ledger.attest_lineage("dynamic-id")
    
    assert len(history) == 3
    assert history[0].state == BeliefState.ACTIVE
    assert history[1].state == BeliefState.CONTESTED
    assert history[2].state == BeliefState.SUBSUMED
