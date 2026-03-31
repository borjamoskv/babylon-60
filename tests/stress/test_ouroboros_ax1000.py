from unittest.mock import AsyncMock, patch

import pytest

from cortex.engine.ouroboros.ouroboros_daemon import OuroborosDaemon
from cortex.swarm.actuators.protocol import ActuatorResponse


@pytest.mark.asyncio
async def test_ouroboros_ax1000_integration():
    daemon = OuroborosDaemon()

    # Mock ghost_hunt to return a dummy bounty that passes ExergyGate (>10x ROI)
    async def mock_ghost_hunt():
        return [
            {
                "id": "test_bounty",
                "expected_yield": 1000.0,
                "compute_cost": 50.0,
                "url": "https://github.com/org/repo/issues/1",
            }
        ]

    daemon.ghost_hunt = mock_ghost_hunt

    with patch(
        "cortex.swarm.manager.SwarmManager.deploy_squad", new_callable=AsyncMock
    ) as mock_deploy:
        mock_deploy.return_value = [
            ActuatorResponse(
                content="PR created successfully",
                status="success",
                metadata={"exergy": 950.0, "cycles": 10},
            )
        ]

        # We need to run cycle but shut it down afterwards
        # Actually run_cycle initializes and shuts down automatically
        await daemon.run_cycle()

        mock_deploy.assert_called_once()
        kwargs = mock_deploy.call_args.kwargs
        assert kwargs["squad_type"] == "OMEGA"
        assert kwargs["count"] == 100
        assert "target" in kwargs["task"] or "targeting" in kwargs["task"]
