from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.core import app as core_app
from cortex.routes import health as health_routes
from cortex.routes import runtime as runtime_routes


def test_runtime_health_route_uses_canonical_builder(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def fake_build(db_path: str) -> dict:
        seen["db_path"] = db_path
        return {
            "status": "degraded",
            "components": {"db": "degraded"},
            "degraded_features": ["db"],
            "warnings": ["db: degraded (40%)"],
            "score": 62.5,
            "grade": "C",
            "summary": "CORTEX Health: 62.5/100",
            "trend": "stable",
            "recommendations": ["compact db"],
            "sub_indices": {"storage": 55.0},
            "component_details": {
                "db": {
                    "status": "degraded",
                    "value": 40.0,
                    "latency_ms": 3.2,
                    "description": "db size pressure",
                    "remediation": "compact db",
                }
            },
            "checked_at": "2026-04-14T12:00:00+00:00",
        }

    monkeypatch.setattr(runtime_routes, "build_runtime_health_payload", fake_build)

    app = FastAPI()
    app.include_router(runtime_routes.router)
    app.state.engine = SimpleNamespace(_db_path="/tmp/runtime-health.db")

    with TestClient(app) as client:
        response = client.get("/v1/runtime/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["score"] == 62.5
    assert seen["db_path"] == "/tmp/runtime-health.db"


def test_runtime_health_route_openapi_uses_runtime_health_schema() -> None:
    app = FastAPI()
    app.include_router(runtime_routes.router)

    schema = app.openapi()
    runtime_schema = schema["components"]["schemas"]["RuntimeHealthResponse"]

    assert runtime_schema["properties"]["status"]["enum"] == ["ok", "degraded", "blocked"]
    assert runtime_schema["properties"]["grade"]["enum"] == ["S", "A", "B", "C", "D", "F"]


def test_health_report_route_uses_canonical_report_builder(monkeypatch) -> None:
    seen: dict[str, str] = {}

    class _FakeReport:
        def to_dict(self) -> dict:
            return {
                "score": {"score": 88.0, "grade": "A", "healthy": True, "timestamp": "now"},
                "recommendations": ["keep verifying"],
                "warnings": [],
                "trend": "stable",
                "is_critical": False,
                "db_path": "/tmp/runtime-health.db",
            }

    def fake_build(db_path: str) -> _FakeReport:
        seen["db_path"] = db_path
        return _FakeReport()

    monkeypatch.setattr(health_routes, "build_health_report", fake_build)

    app = FastAPI()
    app.include_router(health_routes.router)
    app.state.engine = SimpleNamespace(_db_path="/tmp/runtime-health.db")

    with TestClient(app) as client:
        response = client.get("/v1/health/report")

    assert response.status_code == 200
    assert response.json()["trend"] == "stable"
    assert seen["db_path"] == "/tmp/runtime-health.db"


def test_legacy_health_endpoint_serializes_grade_as_letter(monkeypatch) -> None:
    from cortex.extensions.health import Grade, HealthScore

    monkeypatch.setattr(
        "cortex.extensions.health.collect_health_score",
        lambda db_path: HealthScore(score=72.5, grade=Grade.GOOD),
    )

    original_engine = getattr(core_app.state, "engine", None)
    core_app.state.engine = SimpleNamespace(_db_path="/tmp/legacy-health.db")

    try:
        with TestClient(core_app) as client:
            response = client.get("/health")
    finally:
        if original_engine is None and hasattr(core_app.state, "engine"):
            delattr(core_app.state, "engine")
        else:
            core_app.state.engine = original_engine

    assert response.status_code == 200
    assert response.json()["health_index"]["grade"] == "B"


def test_boot_recovery_returns_default_clean_report_when_absent() -> None:
    app = FastAPI()
    app.include_router(runtime_routes.router)
    app.state.engine = SimpleNamespace(_db_path="/tmp/runtime-health.db")

    with TestClient(app) as client:
        response = client.get("/v1/runtime/boot_recovery")

    assert response.status_code == 200
    assert response.json() == {
        "status": "clean",
        "recovered_items": 0,
        "failed_items": 0,
        "last_checkpoint_id": None,
        "warnings": [],
    }


def test_boot_recovery_requires_engine() -> None:
    app = FastAPI()
    app.include_router(runtime_routes.router)

    with TestClient(app) as client:
        response = client.get("/v1/runtime/boot_recovery")

    assert response.status_code == 500
    assert response.json()["detail"] == "Engine not available"
