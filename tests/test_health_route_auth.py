from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.extensions.health.models import Grade, HealthScore
from cortex.routes import health as health_routes


def _client(auth_result: AuthResult | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(health_routes.router)
    app.state.engine = SimpleNamespace(_db_path="/tmp/test.db")
    if auth_result is not None:
        app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def _patch_health(monkeypatch) -> None:
    monkeypatch.setattr(
        health_routes.HealthCollector,
        "collect_all",
        lambda self: [SimpleNamespace(name="db", value=1.0, weight=1.0, unit="ratio", collected_at="now")],
    )
    monkeypatch.setattr(
        health_routes.HealthScorer,
        "score",
        lambda metrics: HealthScore(score=95.0, grade=Grade.EXCELLENT, metrics=[]),
    )
    monkeypatch.setattr(health_routes.HealthScorer, "summarize", lambda hs: "healthy")


def test_health_check_remains_public(monkeypatch) -> None:
    _patch_health(monkeypatch)
    client = _client()

    response = client.get("/v1/health/check")

    assert response.status_code == 200
    assert response.json()["healthy"] is True


def test_health_report_requires_auth(monkeypatch) -> None:
    _patch_health(monkeypatch)
    client = _client()

    response = client.get("/v1/health/report")

    assert response.status_code == 401


def test_health_metrics_requires_auth(monkeypatch) -> None:
    _patch_health(monkeypatch)
    client = _client()

    response = client.get("/v1/health/metrics")

    assert response.status_code == 401


def test_health_report_allows_authenticated_read(monkeypatch) -> None:
    _patch_health(monkeypatch)
    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-health",
            permissions=["read"],
            key_name="health-key",
        )
    )

    response = client.get("/v1/health/report")

    assert response.status_code == 200
    assert response.json()["score"]["grade"] == "A"
