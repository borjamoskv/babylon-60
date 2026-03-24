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
@respx.mock
async def test_fetch_from_algora_mock():
    service = BountyService(reward_threshold=100.0)

    # Mock Algora API (simulated)
    # Note: Algora might have a different API, we use a placeholder for now
    respx.get(url__contains="algora.io").mock(return_value=Response(200, json=[
        {
            "id": "alg1",
            "title": "Enhance RAG Pipeline",
            "reward": 423.30,
            "url": "https://algora.io/isaac/bounties/clq18zr98000ejs0gt0nv7gwu",
            "repository": {"full_name": "aietal/isaac"},
            "issue": {"number": 123}
        }
    ]))

    # This method is not yet implemented, but this is the test interface
    leads = await service._fetch_from_algora()
    assert len(leads) == 1
    assert leads[0].reward_usd == 423.30
    assert leads[0].repo == "aietal/isaac"

@pytest.mark.asyncio
async def test_rank_leads_exergy_filter():
    service = BountyService(reward_threshold=300.0)

    leads = [
        BountyLead(number=1, title="Low exergy", url="", reward_usd=150.0, difficulty="high", score=5.0, repo="r1"),
        BountyLead(number=2, title="High exergy", url="", reward_usd=1000.0, difficulty="medium", score=8.0, repo="r2"),
    ]

    ranked = service.rank_leads(leads)
    assert len(ranked) == 1
    assert ranked[0].number == 2
