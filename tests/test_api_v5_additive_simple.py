from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes import build_api_router

TEST_AUTH = AuthResult(
    authenticated=True,
    tenant_id="default",
    permissions=["read", "write", "admin"],
    key_name="test_agent",
)


async def override_auth() -> AuthResult:
    return TEST_AUTH


def _fresh_api_app() -> FastAPI:
    """Build a fresh API app instance without the global lifespan-managed state."""
    app = FastAPI()
    app.include_router(build_api_router())
    return app


def test_api_router_mounts_facts_routes_without_lifespan() -> None:
    app = _fresh_api_app()
    fact_paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/v1/facts")
    }

    assert "/v1/facts/verify" in fact_paths
    assert "/v1/facts/{fact_id}/history" in fact_paths


@pytest.fixture
def mock_engine() -> AsyncMock:
    engine = AsyncMock()
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

    report = MagicMock()
    report.source_fact_id = 99
    report.affected_count = 2
    report.confidence_changes = [{"fact_id": 100, "old": "C5", "new": "C3"}]
    engine.propagate_taint.return_value = report
    engine.verify_ledger.return_value = {"valid": True, "tx_count": 11, "roots_checked": 3}
    return engine


@pytest.fixture
def client(mock_engine: AsyncMock) -> TestClient:
    app = _fresh_api_app()
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    app.dependency_overrides[require_auth] = override_auth

    with TestClient(app) as client:
        yield client


def test_fact_history_endpoint(client: TestClient) -> None:
    resp = client.get("/v1/facts/1/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_taint_propagation_endpoint(client: TestClient) -> None:
    resp = client.post("/v1/facts/99/taint")
    assert resp.status_code == 200
    assert resp.json()["source_id"] == 99


def test_trust_endpoints_are_not_mounted_in_fresh_api_app(client: TestClient) -> None:
    resp = client.get("/v1/trust/profiles/test_agent")
    assert resp.status_code == 404

    resp = client.get("/v1/trust/compliance")
    assert resp.status_code == 404


def test_facts_verify_uses_tx_count(client: TestClient) -> None:
    resp = client.get("/v1/facts/verify")
    assert resp.status_code == 200
    assert resp.json()["transactions_checked"] == 11


def test_ledger_status_is_not_mounted_in_fresh_api_app(client: TestClient) -> None:
    resp = client.get("/v1/ledger/status")
    assert resp.status_code == 404
