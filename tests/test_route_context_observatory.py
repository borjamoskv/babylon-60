from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import context as context_router
from cortex.routes import observatory as observatory_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeEngine:
    @asynccontextmanager
    async def session(self):
        yield object()


def test_context_infer_applies_signal_and_response_limits(monkeypatch) -> None:
    collector_args: dict[str, object] = {}

    class _FakeCollector:
        def __init__(self, **kwargs):
            collector_args.update(kwargs)

        async def collect_all(self):
            return ["s1", "s2", "s3"]

    class _Signal:
        def __init__(self, idx: int) -> None:
            self.idx = idx

        def to_dict(self) -> dict[str, object]:
            return {
                "source": f"src-{self.idx}",
                "signal_type": "test",
                "content": f"signal-{self.idx}",
                "project": "alpha",
                "timestamp": "2026-01-01T00:00:00Z",
                "weight": 1.0,
            }

    class _FakeInference:
        def __init__(self, conn=None):
            self.conn = conn

        def infer(self, signals):
            assert signals == ["s1", "s2", "s3"]
            return SimpleNamespace(
                active_project="alpha",
                confidence="high",
                signals_used=3,
                summary="ok",
                top_signals=[_Signal(i) for i in range(4)],
                projects_ranked=[("alpha", 0.9), ("beta", 0.5), ("gamma", 0.2)],
            )

        async def infer_and_persist(self, signals):
            return self.infer(signals)

    monkeypatch.setattr(context_router, "ContextCollector", _FakeCollector)
    monkeypatch.setattr(context_router, "ContextInference", _FakeInference)
    monkeypatch.setattr("cortex.config.CONTEXT_MAX_SIGNALS", 50)
    monkeypatch.setattr("cortex.config.CONTEXT_WORKSPACE_DIR", "/tmp")
    monkeypatch.setattr("cortex.config.CONTEXT_GIT_ENABLED", False)

    app = FastAPI()
    app.include_router(context_router.router)
    auth_dep = _dependency_for(
        "/v1/context/infer",
        "GET",
        _route_by_path(context_router.router, "/v1/context/infer", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-context",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeEngine()

    with TestClient(app) as client:
        response = client.get(
            "/v1/context/infer?persist=false&signal_limit=3&top_signals_limit=2&projects_limit=1"
        )

    assert response.status_code == 200
    body = response.json()
    assert collector_args["max_signals"] == 3
    assert len(body["top_signals"]) == 2
    assert len(body["projects_ranked"]) == 1


def test_context_signals_applies_limit(monkeypatch) -> None:
    collector_args: dict[str, object] = {}

    class _FakeCollector:
        def __init__(self, **kwargs):
            collector_args.update(kwargs)

        async def collect_all(self):
            return [
                SimpleNamespace(
                    to_dict=lambda idx=i: {
                        "source": f"src-{idx}",
                        "signal_type": "test",
                        "content": f"signal-{idx}",
                        "project": "alpha",
                        "timestamp": "2026-01-01T00:00:00Z",
                        "weight": 1.0,
                    }
                )
                for i in range(2)
            ]

    monkeypatch.setattr(context_router, "ContextCollector", _FakeCollector)
    monkeypatch.setattr("cortex.config.CONTEXT_MAX_SIGNALS", 50)
    monkeypatch.setattr("cortex.config.CONTEXT_WORKSPACE_DIR", "/tmp")
    monkeypatch.setattr("cortex.config.CONTEXT_GIT_ENABLED", False)

    app = FastAPI()
    app.include_router(context_router.router)
    auth_dep = _dependency_for(
        "/v1/context/signals",
        "GET",
        _route_by_path(context_router.router, "/v1/context/signals", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-context",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _FakeEngine()

    with TestClient(app) as client:
        response = client.get("/v1/context/signals?limit=7")

    assert response.status_code == 200
    assert collector_args["max_signals"] == 7
    assert len(response.json()) == 2


def test_observatory_forwards_recent_decisions_limit(monkeypatch) -> None:
    called: dict[str, object] = {}

    monkeypatch.setattr(observatory_router, "_get_daemon_status", lambda: {"status": "ok"})
    monkeypatch.setattr(observatory_router, "_get_dependency_health", lambda: {"status": "ok"})
    monkeypatch.setattr(observatory_router, "_get_effectiveness", lambda: {"cortex": {}})
    monkeypatch.setattr(observatory_router, "_get_evolution_status", lambda: {"status": "idle"})

    def _fake_recent(limit: int):
        called["limit"] = limit
        return []

    monkeypatch.setattr(observatory_router, "_get_recent_decisions", _fake_recent)

    app = FastAPI()
    app.include_router(observatory_router.router)
    auth_dep = _dependency_for(
        "/v1/observatory",
        "GET",
        _route_by_path(observatory_router.router, "/v1/observatory", "GET"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-observatory",
        permissions=["read"],
    )

    with TestClient(app) as client:
        response = client.get("/v1/observatory?recent_decisions_limit=4")

    assert response.status_code == 200
    assert called["limit"] == 4
