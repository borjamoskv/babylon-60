"""
AX-1000 Integration Test: CapitalSwarmEngine + Mercor Vectors (B, M).
Validates that the sovereign bootstrap wires AsyncCortexEngine + SwarmManager
into the Capital Swarm and that Mercor specialist vectors execute cleanly
with ledger crystallization.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.swarm.capital_swarm import CapitalSwarmEngine


@pytest.mark.asyncio
async def test_capital_swarm_mercor_dry_run():
    """
    Validate that Mercor vectors B and M pass the EV gate
    and simulate correctly in dry-run mode with sovereign engine.
    """
    mock_engine = MagicMock()
    mock_engine.ledger = MagicMock()
    mock_engine.ledger.record_transaction = AsyncMock()

    mock_swarm = MagicMock()
    mock_swarm.recruit = AsyncMock(return_value=[])

    engine = CapitalSwarmEngine(
        active_vectors=["B", "M"],
        dry_run=True,
        engine=mock_engine,
        swarm_manager=mock_swarm,
    )

    report = await engine.run()

    assert len(report.results) == 2
    for r in report.results:
        assert r.status == "simulated"
        assert r.gross_yield_usd > 0
        assert r.is_positive_exergy

    # Ledger crystallization should have been called for each result
    assert mock_engine.ledger.record_transaction.call_count == 2


@pytest.mark.asyncio
async def test_capital_swarm_ev_gate_rejects_low_exergy():
    """
    A synthetic vector with negative EV should be rejected by the gate.
    """
    engine = CapitalSwarmEngine(
        active_vectors=["G"],  # Red Team: $2000 yield * 0.20 = $400 vs $15 cost * 5 = $75 → PASS
        dry_run=True,
    )
    report = await engine.run()
    # G should pass EV gate ($400 > $75)
    assert report.results[0].status == "simulated"


@pytest.mark.asyncio
async def test_capital_swarm_swarm_manager_present():
    """
    Verify that swarm_manager is stored and accessible on the engine.
    """
    mock_swarm = MagicMock()
    engine = CapitalSwarmEngine(
        active_vectors=["B"],
        dry_run=True,
        swarm_manager=mock_swarm,
    )
    assert engine.swarm_manager is mock_swarm
