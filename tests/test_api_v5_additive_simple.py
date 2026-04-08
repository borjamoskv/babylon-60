from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.core import app
from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth, require_permission

# Mock AuthResult for dependency override
mock_auth = MagicMock()
mock_auth.tenant_id = "default"
mock_auth.authenticated = True
mock_auth.permissions = ["read", "write", "admin"]


async def override_auth():
    return mock_auth


def test_core_app_mounts_facts_routes_without_lifespan() -> None:
    fact_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/v1/facts")
    }

    assert "/v1/facts/verify" in fact_paths
    assert "/v1/facts/{fact_id}/history" in fact_paths


@pytest.fixture
def mock_engine():
    engine = AsyncMock()
    # Mock history/causal chain
    engine.get_causal_chain.return_value = [
        {
            "id": 1,
            "project": "test",
            "content": "v1",
            "fact_type": "knowledge",
            "created_at": "2024-01-01",
        },
        {
            "id": 2,
            "project": "test",
            "content": "v2",
            "fact_type": "knowledge",
            "created_at": "2024-01-02",
        },
    ]
    # Mock taint report
    report = MagicMock()
    report.source_fact_id = 99
    report.affected_count = 2
    report.confidence_changes = [{"fact_id": 100, "old": "C5", "new": "C3"}]
    engine.propagate_taint.return_value = report

    # Mock ledger verify and stats
    engine.verify_ledger.return_value = {"valid": True, "tx_count": 11, "roots_checked": 3}

    return engine


@pytest.fixture
def client(mock_engine):
    app.dependency_overrides[get_async_engine] = lambda: mock_engine

    # Define a helper that returns our mock_auth for ANY permission level
    def get_override(perm):
        return override_auth

    # Override the specific dependency factories
    app.dependency_overrides[require_auth] = override_auth
    # require_permission is a factory, we need to override the SPECIFIC instances used in routes
    # But since we can't easily guess all instances, we override the common ones.
    # The actual routes use Depends(require_permission("read")), etc.
    # FastAPI keys these by the function object and its arguments.
    for perm in ["read", "write", "admin"]:
        app.dependency_overrides[require_permission(perm)] = override_auth

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_fact_history_endpoint(client):
    resp = client.get("/v1/facts/1/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_taint_propagation_endpoint(client):
    resp = client.post("/v1/facts/99/taint")
    assert resp.status_code == 200
    assert resp.json()["source_id"] == 99


def test_trust_endpoints_are_not_mounted_in_core_app(client):
    resp = client.get("/v1/trust/profiles/test_agent")
    assert resp.status_code == 404

    resp = client.get("/v1/trust/compliance")
    assert resp.status_code == 404


def test_facts_verify_uses_tx_count(client):
    resp = client.get("/v1/facts/verify")
    assert resp.status_code == 200
    assert resp.json()["transactions_checked"] == 11


def test_ledger_status_is_not_mounted_in_core_app(client):
    resp = client.get("/v1/ledger/status")
    assert resp.status_code == 404
