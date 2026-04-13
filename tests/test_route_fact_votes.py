from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from cortex.api.core import app
from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth, require_permission

mock_auth = MagicMock()
mock_auth.tenant_id = "tenant-alpha"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]
mock_auth.key_name = "router-agent"


async def override_auth():
    return mock_auth


@pytest.fixture
def vote_client():
    engine = AsyncMock()

    app.dependency_overrides[get_async_engine] = lambda: engine
    app.dependency_overrides[require_auth] = override_auth
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    client = TestClient(app)
    try:
        yield client, engine
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_vote_endpoint_contract_stays_stable(vote_client) -> None:
    client, engine = vote_client
    engine.get_fact.side_effect = [
        {
            "id": 41,
            "tenant_id": "tenant-alpha",
            "confidence": "C3",
        },
        {
            "id": 41,
            "tenant_id": "tenant-alpha",
            "confidence": "C5",
        },
    ]
    engine.vote_v2.return_value = 0.75

    response = client.post("/v1/facts/41/vote", json={"value": 1})

    assert response.status_code == 200
    assert response.json() == {
        "fact_id": 41,
        "agent": "router-agent",
        "vote": 1,
        "new_consensus_score": 0.75,
        "confidence": "C5",
        "status": "recorded",
    }
    engine.vote_v2.assert_any_call(41, "router-agent", 1)


def test_vote_v2_endpoint_contract_stays_stable(vote_client) -> None:
    client, engine = vote_client
    engine.get_fact.side_effect = [
        {
            "id": 52,
            "tenant_id": "tenant-alpha",
            "confidence": "C2",
        },
        {
            "id": 52,
            "tenant_id": "tenant-alpha",
            "confidence": "C4",
        },
    ]
    engine.vote_v2.return_value = 0.25

    response = client.post(
        "/v1/facts/52/vote-v2",
        json={"agent_id": "weighted-agent", "vote": -1},
    )

    assert response.status_code == 200
    assert response.json() == {
        "fact_id": 52,
        "agent": "weighted-agent",
        "vote": -1,
        "new_consensus_score": 0.25,
        "confidence": "C4",
        "status": "recorded",
    }
    engine.vote_v2.assert_any_call(52, "weighted-agent", -1)
