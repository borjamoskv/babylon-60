from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.daemon.frontier import FrontierDaemon
from cortex.services.bounty_service import BountyService
from cortex.swarm.specialists import GoogleJulesOmega


@pytest.mark.asyncio
async def test_bounty_service_scan():
    service = BountyService(ledger=None)
    leads = await service.scan_repository("test_owner", "test_repo")
    assert len(leads) > 0
    assert leads[0].reward_usd == 500.0


@pytest.mark.asyncio
async def test_jules_actuator_graceful_degradation():
    """When JULES_API_KEY is absent, falls back to simulated response."""
    actuator = GoogleJulesOmega()
    actuator._api_key = None  # Force simulation path

    response = await actuator.execute("Solve bug #42")
    assert "Jules AI" in response["content"]
    assert response["metadata"]["exergy_yield"] > 0
    assert response["metadata"]["live"] is False


@pytest.mark.asyncio
async def test_jules_actuator_live_api_payload():
    """Verify correct payload structure sent to Jules API."""
    actuator = GoogleJulesOmega()
    actuator._api_key = "test-key-not-real"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "sessions/test-session-123",
        "status": "ACTIVE",
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await actuator.execute(
            "Fix security vulnerability in auth module",
            context={"repo": "borjamoskv/Cortex-Persist", "branch": "main"},
        )

    assert response["metadata"]["live"] is True
    assert response["metadata"]["session_name"] == "sessions/test-session-123"
    assert response["metadata"]["api_status"] == "ACTIVE"
    assert "session created" in response["content"].lower()

    # Verify the POST was called with correct payload
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.args[0] == GoogleJulesOmega.JULES_API_URL
    payload = call_kwargs.kwargs["json"]
    assert payload["automationMode"] == "AUTO_CREATE_PR"
    assert payload["sourceContext"]["source"] == "sources/github/borjamoskv/Cortex-Persist"
    assert payload["requirePlanApproval"] is False


@pytest.mark.asyncio
async def test_jules_actuator_api_failure_fallback():
    """When API call fails, falls back to simulated response with reason."""
    actuator = GoogleJulesOmega()
    actuator._api_key = "test-key-not-real"

    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await actuator.execute("Solve bug #99")

    assert response["metadata"]["live"] is False
    assert "Connection refused" in response["metadata"]["fallback_reason"]
    assert "Jules AI" in response["content"]


@pytest.mark.asyncio
async def test_frontier_daemon_ingestion_with_bounties():
    # Mock engine and ledger
    mock_engine = MagicMock()
    mock_engine.ledger = AsyncMock()

    daemon = FrontierDaemon(engine=mock_engine)
    daemon._log_evolution = MagicMock()

    # Run ingestion cycle
    await daemon._run_ingestion()

    # Verify that log_evolution was called for ingestion and bounty
    calls = [call.args[0] for call in daemon._log_evolution.call_args_list]
    assert "ingestion" in calls
    assert "bounty" in calls
