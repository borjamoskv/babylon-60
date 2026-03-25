# CORTEX-TAINT: cazarecompensas-agent:ab12cd34:1742878308
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from cortex.services.bounty_service import BountyLead, BountyService


@pytest.mark.asyncio
@respx.mock
async def test_fetch_from_github_mock():
    service = BountyService(reward_threshold=100.0)

    # Mock GitHub API
    respx.get("https://api.github.com/search/issues").mock(return_value=Response(200, json={
        "items": [
            {
                "title": "Fix bug $500",
                "body": "Bounty available",
                "html_url": "https://github.com/owner/repo/issues/1",
                "number": 1,
                "labels": [{"name": "bounty"}, {"name": "high"}]
            }
        ]
    }))

    leads = await service._fetch_from_github("query")
    assert len(leads) == 1
    assert leads[0].reward_usd == 500.0
    assert leads[0].repo == "owner/repo"


@pytest.mark.asyncio
async def test_rank_leads_exergy_filter():
    service = BountyService(reward_threshold=300.0)

    leads = [
        BountyLead(number=1, title="Low exergy", url="", reward_usd=150.0, difficulty="high", score=5.0, repo="r1"),
        BountyLead(number=2, title="High exergy", url="", reward_usd=1000.0, difficulty="medium", score=8.0, repo="r2"),
    ]

    ranked = await service.rank_leads(leads)
    assert len(ranked) == 1
    assert ranked[0].number == 2


@pytest.mark.asyncio
async def test_scan_global_language_filter():
    """Test that scan_global accepts language filter parameter."""
    service = BountyService(reward_threshold=100.0)

    with patch.object(service, "_fetch_from_github", new_callable=AsyncMock, return_value=[]) as mock_fetch:
        await service.scan_global(max_results=10, languages=["python", "rust"])
        mock_fetch.assert_awaited_once()
        query = mock_fetch.call_args[0][0]
        assert "language:python" in query
        assert "language:rust" in query


@pytest.mark.asyncio
async def test_scan_global_no_language_filter():
    """Test that scan_global works without language filter."""
    service = BountyService(reward_threshold=100.0)

    with patch.object(service, "_fetch_from_github", new_callable=AsyncMock, return_value=[]) as mock_fetch:
        await service.scan_global(max_results=10)
        mock_fetch.assert_awaited_once()
        query = mock_fetch.call_args[0][0]
        assert "language:" not in query


@pytest.mark.asyncio
async def test_scan_all_delegates_to_sovereign_scanner():
    """Test that scan_all delegates to SovereignBountyScanner."""
    from cortex.swarm.bounty_scanner import BountyOpportunity

    mock_opps = [
        BountyOpportunity(
            id="test-1", title="Test Bounty", repo="owner/repo",
            platform="algora", reward_usd=500.0, confidence=0.8,
            complexity=5, url="https://test.com/1",
        ),
    ]

    service = BountyService(reward_threshold=100.0)

    with patch("cortex.swarm.bounty_scanner.SovereignBountyScanner") as MockScanner:
        mock_instance = MockScanner.return_value
        mock_instance.scan_all = AsyncMock(return_value=mock_opps)

        leads = await service.scan_all(min_usd=100.0)
        assert len(leads) == 1
        assert leads[0].title == "Test Bounty"
        assert leads[0].reward_usd == 500.0
        assert leads[0].difficulty == "medium"  # complexity 5 → medium


def test_complexity_to_difficulty():
    """Test the static complexity→difficulty mapper."""
    assert BountyService._complexity_to_difficulty(1) == "low"
    assert BountyService._complexity_to_difficulty(3) == "low"
    assert BountyService._complexity_to_difficulty(4) == "medium"
    assert BountyService._complexity_to_difficulty(6) == "medium"
    assert BountyService._complexity_to_difficulty(7) == "high"
    assert BountyService._complexity_to_difficulty(10) == "high"
