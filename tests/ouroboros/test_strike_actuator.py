"""
Tests for the Ouroboros Strike Actuator
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.engine.ouroboros.strike_actuator import StrikeActuator, StrikeVector


@pytest.mark.asyncio
async def test_strike_actuator_dry_run_returns_cleared():
    actuator = StrikeActuator(use_dry_run=True)
    payload = {
        "id": "bounty_4591",
        "url": "https://algora.io/bounty/4591",
        "expected_yield": 1200.0,
        "compute_cost": 5.0,
    }
    mock_swarm = MagicMock()

    result = await actuator.strike(StrikeVector.VECTOR_A_BOUNTY, payload, mock_swarm)

    assert result["status"] == "cleared_dry_run"
    assert result["net_yield"] == 1200.0
    assert result["compute_cost"] == 5.0
    assert result["strike_vector"] == "algora_bounty"


@pytest.mark.asyncio
async def test_strike_actuator_live_dispatches_to_omega_swarm():
    """OMEGA Swarm path: deploy_squad is awaited, returns sovereign session_id.

    The legacy Devin API dispatch path was replaced in v6.x by the native
    CORTEX OMEGA Swarm (AX-1000). This test validates the current contract.
    """
    actuator = StrikeActuator(use_dry_run=False)

    # deploy_squad is awaited inside strike() — must be AsyncMock
    mock_swarm = MagicMock()
    mock_swarm.deploy_squad = AsyncMock(
        return_value=[
            {
                "status": "deployed",
                "metadata": {"exergy": 0.92, "cycles": 3},
            }
        ]
    )

    payload = {
        "id": "bounty_1111",
        "url": "https://algora.io/bounty/1111",
        "expected_yield": 800.0,
        "compute_cost": 20.0,
    }

    result = await actuator.strike(StrikeVector.VECTOR_A_BOUNTY, payload, mock_swarm)

    assert result["status"] == "deployed"
    assert result["strike_vector"] == "algora_bounty"
    assert result["session_id"] == "native_omega_swarm"
    assert result["net_yield"] == 800.0

    # Verify OMEGA Swarm was called with the sovereign dispatch parameters
    mock_swarm.deploy_squad.assert_awaited_once()
    call_kwargs = mock_swarm.deploy_squad.call_args
    assert call_kwargs.kwargs.get("count") == 100
    assert call_kwargs.kwargs.get("squad_type") == "OMEGA"
