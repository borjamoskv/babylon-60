# [C5-REAL] Exergy-Maximized
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from cortex.core.lineage import LineageVerifier, LineageNode

class DummyFact:
    def __init__(self, fact_id, content, tx_id, fact_hash, meta=None):
        self.id = fact_id
        self.project = "test_project"
        self.content = content
        self.fact_type = "test_type"
        self.confidence = "high"
        self.created_at = "2026-06-15T00:00:00Z"
        self.tx_id = tx_id
        self.hash = fact_hash
        self.meta = meta or {}

@pytest.mark.asyncio
async def test_lineage_verifier_local_only():
    mock_engine = MagicMock()
    mock_engine.get_fact = AsyncMock(return_value=DummyFact(
        fact_id=1,
        content="Ground truth fact content",
        tx_id="tx_123",
        fact_hash="0x" + "a" * 64
    ))
    
    verifier = LineageVerifier(mock_engine, on_chain_verifier=None)
    node = await verifier.get_lineage(1)
    
    assert node.is_valid is True
    assert node.error is None
    mock_engine.get_fact.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_lineage_verifier_on_chain_success():
    mock_engine = MagicMock()
    mock_engine.get_fact = AsyncMock(return_value=DummyFact(
        fact_id=1,
        content="Telemetry data",
        tx_id="tx_123",
        fact_hash="0x" + "a" * 64
    ))
    
    mock_verifier = MagicMock()
    mock_verifier.connect.return_value = True
    
    mock_call = MagicMock()
    mock_call.call.return_value = True
    mock_verifier.contract.functions.verifyTelemetry.return_value = mock_call
    
    verifier = LineageVerifier(mock_engine, on_chain_verifier=mock_verifier)
    node = await verifier.get_lineage(1)
    
    assert node.is_valid is True
    assert node.error is None
    
    # Verify hex conversion (without 0x)
    hash_bytes = bytes.fromhex("a" * 64)
    mock_verifier.contract.functions.verifyTelemetry.assert_called_once_with(hash_bytes, b"")

@pytest.mark.asyncio
async def test_lineage_verifier_on_chain_failure():
    mock_engine = MagicMock()
    mock_engine.get_fact = AsyncMock(return_value=DummyFact(
        fact_id=1,
        content="Tampered telemetry data",
        tx_id="tx_123",
        fact_hash="0x" + "b" * 64
    ))
    
    mock_verifier = MagicMock()
    mock_verifier.connect.return_value = True
    
    mock_call = MagicMock()
    mock_call.call.return_value = False
    mock_verifier.contract.functions.verifyTelemetry.return_value = mock_call
    
    verifier = LineageVerifier(mock_engine, on_chain_verifier=mock_verifier)
    node = await verifier.get_lineage(1)
    
    assert node.is_valid is False
    assert node.error == "Fact telemetry hash not verified on-chain."

@pytest.mark.asyncio
async def test_lineage_verifier_on_chain_exception():
    mock_engine = MagicMock()
    mock_engine.get_fact = AsyncMock(return_value=DummyFact(
        fact_id=1,
        content="Telemetry",
        tx_id="tx_123",
        fact_hash="0x" + "a" * 64
    ))
    
    mock_verifier = MagicMock()
    mock_verifier.connect.side_effect = Exception("RPC Network Timeout")
    
    verifier = LineageVerifier(mock_engine, on_chain_verifier=mock_verifier)
    node = await verifier.get_lineage(1)
    
    # Should fall back to invalid with the error description
    assert node.is_valid is False
    assert "On-chain verification error" in node.error
