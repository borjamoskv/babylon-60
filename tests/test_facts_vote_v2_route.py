from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.routes.facts import cast_vote_v2
from cortex.types.models import VoteV2Request


class _DummyRequest:
    headers: dict[str, str] = {}


@pytest.mark.asyncio
async def test_cast_vote_v2_uses_consensus_vote_v2() -> None:
    engine = AsyncMock()
    engine.get_fact.side_effect = [
        {"id": 5, "tenant_id": "tenant-a", "confidence": "stated"},
        {"id": 5, "tenant_id": "tenant-a", "confidence": "verified"},
    ]
    engine.consensus = SimpleNamespace(vote_v2=AsyncMock(return_value=0.92))
    auth = SimpleNamespace(tenant_id="tenant-a", permissions=["write"])

    response = await cast_vote_v2(
        fact_id=5,
        req=VoteV2Request(agent_id="agent-1", vote=1, reason="verified by quorum"),
        request=_DummyRequest(),
        auth=auth,
        engine=engine,
    )

    engine.consensus.vote_v2.assert_awaited_once_with(
        fact_id=5,
        agent_id="agent-1",
        value=1,
        reason="verified by quorum",
    )
    assert response.fact_id == 5
    assert response.agent == "agent-1"
    assert response.new_consensus_score == 0.92
    assert response.confidence == "verified"
