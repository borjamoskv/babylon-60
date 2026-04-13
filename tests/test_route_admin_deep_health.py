from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.database.schema import SCHEMA_VERSION
from cortex.routes import admin as admin_router
from cortex.routes import context as context_router


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _Engine:
    def _get_sync_conn(self):
        return object()


def test_deep_health_contract_stays_stable_when_healthy(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_router,
        "_build_health_probes",
        lambda conn, request, schema_version: {
            "database": lambda: ("healthy", True, {"detail": "Database responsive"}),
            "schema": lambda: ("healthy", True, {"version": schema_version}),
        },
    )
    monkeypatch.setattr(context_router, "get_p95_context_latency", lambda: 12.5)

    app = FastAPI()
    app.include_router(admin_router.router)
    route = _route_by_path(admin_router.router, "/v1/health/deep", "GET")
    engine_dep = route.dependant.dependencies[2].call
    auth_dep = route.dependant.dependencies[3].call
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-health",
        permissions=["read"],
    )
    app.dependency_overrides[engine_dep] = lambda: _Engine()

    with TestClient(app) as client:
        response = client.get("/v1/health/deep")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["schema_version"] == SCHEMA_VERSION
    assert body["checks"]["database"]["detail"] == "Database responsive"
    assert body["checks"]["schema"]["version"] == SCHEMA_VERSION
    assert body["p95_latency_ms"] == 12.5


def test_deep_health_contract_stays_stable_when_degraded(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_router,
        "_build_health_probes",
        lambda conn, request, schema_version: {
            "database": lambda: ("unhealthy", False, {"detail": "db locked"}),
        },
    )
    monkeypatch.setattr(context_router, "get_p95_context_latency", lambda: 9.0)

    app = FastAPI()
    app.include_router(admin_router.router)
    route = _route_by_path(admin_router.router, "/v1/health/deep", "GET")
    engine_dep = route.dependant.dependencies[2].call
    auth_dep = route.dependant.dependencies[3].call
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-health",
        permissions=["read"],
    )
    app.dependency_overrides[engine_dep] = lambda: _Engine()

    with TestClient(app) as client:
        response = client.get("/v1/health/deep")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"]["status"] == "unhealthy"
    assert body["checks"]["database"]["detail"] == "db locked"
    assert body["p95_latency_ms"] == 9.0
