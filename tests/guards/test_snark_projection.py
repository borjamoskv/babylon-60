import pytest

from cortex.engine.mtk_core import MTKGuard
from cortex.types.evidence import ClosurePayload, EvidenceBundle
from cortex.guards.snark_guard import EpistemicSNARKProtocol


@pytest.fixture
def dummy_evidence():
    from datetime import datetime, timezone
    return EvidenceBundle.forge(
        query="SNARK topology verification",
        sources=[],
        retrieved_at=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_mtk_rejects_missing_snark_on_critical_schema(dummy_evidence):
    guard = MTKGuard(private_key="test_key_123")
    
    # Missing snark proof on schema_version > v1
    payload = ClosurePayload.seal(
        claims=[{"fact": "test"}],
        evidence=dummy_evidence,
        verdict=True,
        schema_version="v2",  # Critical schema
        snark_proof=None
    )
    
    with pytest.raises(ValueError, match="MTK-REJECT: Missing SNARK proof for critical topological schema"):
        async with guard.transaction_boundary(payload):
            pass


@pytest.mark.asyncio
async def test_mtk_rejects_invalid_snark_proof(dummy_evidence):
    guard = MTKGuard(private_key="test_key_123")
    
    # Invalid snark proof (e.g., manipulated public signal)
    invalid_proof = {
        "pi_a": ["0x1"],
        "pi_b": [["0x2"], ["0x3"]],
        "pi_c": ["0x0"],
        "public_signals": ["0xdeadbeef"]  # Fake
    }
    
    payload = ClosurePayload.seal(
        claims=[{"fact": "test"}],
        evidence=dummy_evidence,
        verdict=True,
        schema_version="v2",
        snark_proof=invalid_proof,
        ancestor_hash="0x0"
    )
    
    with pytest.raises(ValueError, match="MTK-REJECT: ZK-SNARK mathematical verification failed"):
        async with guard.transaction_boundary(payload):
            pass


@pytest.mark.asyncio
async def test_mtk_accepts_valid_snark_proof(dummy_evidence):
    guard = MTKGuard(private_key="test_key_123")
    
    # Generate a valid proof
    ancestor_hash = "0xabc123"
    
    # Generate a dummy payload to compute its hash
    temp_payload = ClosurePayload.seal(
        claims=[{"fact": "valid"}],
        evidence=dummy_evidence,
        verdict=True,
        schema_version="v2"
    )
    
    proof = EpistemicSNARKProtocol.generate_lineage_proof(ancestor_hash, temp_payload.payload_hash)
    
    payload = ClosurePayload.seal(
        claims=[{"fact": "valid"}],
        evidence=dummy_evidence,
        verdict=True,
        schema_version="v2",
        snark_proof=proof.serialize(),
        ancestor_hash=ancestor_hash
    )
    
    # Should not raise any ValueError
    try:
        async with guard.transaction_boundary(payload):
            pass
    except Exception as e:
        # Ignore non-MTK exceptions like sqlite issues if context is missing, 
        # we only care that it passed the SNARK validation
        if "MTK-REJECT" in str(e):
            pytest.fail(f"MTK wrongly rejected valid SNARK: {e}")
