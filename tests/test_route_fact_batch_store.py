from unittest.mock import AsyncMock, MagicMock, call

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
def batch_client():
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


def test_batch_store_contract_stays_stable_with_partial_failures(batch_client) -> None:
    client, engine = batch_client
    engine.store.side_effect = [101, ValueError("guard failed"), 103]

    response = client.post(
        "/v1/facts/batch",
        json={
            "memories": [
                {
                    "project": "alpha",
                    "content": "first",
                    "type": "knowledge",
                    "tags": ["a"],
                    "source": "seed",
                    "metadata": {"rank": 1},
                },
                {
                    "project": "alpha",
                    "content": "second",
                    "type": "knowledge",
                    "tags": [],
                },
                {
                    "project": "beta",
                    "content": "third",
                    "type": "decision",
                    "tags": ["b"],
                    "parent_decision_id": 7,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "stored": 2,
        "ids": [101, 103],
        "errors": [{"index": 1, "error": "Failed to store fact"}],
        "total_requested": 3,
    }
    assert engine.store.await_args_list == [
        call(
            project="alpha",
            content="first",
            tenant_id="tenant-alpha",
            fact_type="knowledge",
            tags=["a"],
            source="seed",
            meta={"rank": 1},
            parent_decision_id=None,
        ),
        call(
            project="alpha",
            content="second",
            tenant_id="tenant-alpha",
            fact_type="knowledge",
            tags=[],
            source=None,
            meta={},
            parent_decision_id=None,
        ),
        call(
            project="beta",
            content="third",
            tenant_id="tenant-alpha",
            fact_type="decision",
            tags=["b"],
            source=None,
            meta={},
            parent_decision_id=7,
        ),
    ]
