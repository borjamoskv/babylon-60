from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine, get_engine
from cortex.auth.models import AuthResult
from cortex.cli.tips import Tip, TipCategory
from cortex.engine import CortexEngine
from cortex.engine.trust_registry import TrustRegistry
from cortex.routes import admin as admin_router
from cortex.routes import facts as facts_router
from cortex.routes import tips as tips_router
from cortex.types.models import CheckpointResponse


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _permission_dependency_for(router, path: str, method: str) -> Callable:
    route = _route_by_path(router, path, method)
    for dependency in route.dependant.dependencies:
        if getattr(dependency.call, "__name__", "") == "checker":
            return dependency.call
    raise AssertionError(f"Permission dependency not found: {method} {path}")


def test_cortex_engine_exposes_phase1_runtime_surface() -> None:
    engine = CortexEngine(":memory:", auto_embed=False)

    for method_name in (
        "register_agent",
        "get_agent",
        "list_agents",
        "propagate_taint",
        "get_trust_registry",
        "create_checkpoint",
    ):
        assert hasattr(engine, method_name)

    registry = engine.get_trust_registry()
    assert isinstance(registry, TrustRegistry)


def test_checkpoint_response_accepts_hash_identifier() -> None:
    response = CheckpointResponse(
        checkpoint_id="abc123root",
        message="Merkle checkpoint created successfully",
    )

    assert response.checkpoint_id == "abc123root"


class _FakeExportEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def get_all_active_facts(self, *, project: str, tenant_id: str):
        from cortex.engine.models import Fact

        self.calls.append({"project": project, "tenant_id": tenant_id})
        return [
            Fact(
                id=1,
                tenant_id=tenant_id,
                project=project,
                content="alpha fact",
                fact_type="knowledge",
                created_at="2026-01-01T00:00:00Z",
            )
        ]

    async def search(self, *args, **kwargs):
        raise AssertionError("export_project should not call search()")


def test_export_project_uses_active_facts_and_authenticated_tenant(tmp_path: Path) -> None:
    fake_engine = _FakeExportEngine()
    target = Path("phase1-export.json")
    if target.exists():
        target.unlink()

    app = FastAPI()
    app.include_router(admin_router.router)
    auth_dep = _permission_dependency_for(admin_router.router, "/v1/projects/{project}/export", "GET")
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-export",
        permissions=["admin"],
    )
    app.dependency_overrides[get_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.get(f"/v1/projects/alpha/export?path={target}")

    try:
        assert response.status_code == 200
        assert fake_engine.calls == [{"project": "alpha", "tenant_id": "tenant-export"}]
        assert target.exists()
        assert "alpha fact" in target.read_text(encoding="utf-8")
    finally:
        if target.exists():
            target.unlink()


class _FakeVoteEngine:
    def __init__(self) -> None:
        self.vote_v2 = AsyncMock(return_value=0.9)

    async def get_fact(self, fact_id: int, tenant_id: str = "default") -> dict:
        return {"id": fact_id, "tenant_id": tenant_id, "confidence": "C4"}


def test_vote_v2_route_passes_agent_id_keyword() -> None:
    fake_engine = _FakeVoteEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/{fact_id}/vote-v2",
        "POST",
        _route_by_path(facts_router.router, "/v1/facts/{fact_id}/vote-v2", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-vote",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    with TestClient(app) as client:
        response = client.post(
            "/v1/facts/42/vote-v2",
            json={"agent_id": "agent-1", "vote": 1},
        )

    assert response.status_code == 200
    assert fake_engine.vote_v2.await_args.kwargs == {
        "fact_id": 42,
        "agent_id": "agent-1",
        "value": 1,
    }


class _FakeTipsEngine:
    def __init__(self) -> None:
        tip_a = Tip("tip-a", "First", TipCategory.CORTEX, "en")
        tip_b = Tip("tip-b", "Second", TipCategory.DEBUGGING, "en")
        tip_c = Tip("tip-c", "Third", TipCategory.CORTEX, "en", project="alpha")

        self.random = AsyncMock(side_effect=[tip_a, tip_b])
        self.all_tips = AsyncMock(return_value=[tip_a, tip_b, tip_c])
        self.for_category = AsyncMock(return_value=[tip_a, tip_c])
        self.for_project = AsyncMock(return_value=[tip_c, tip_a])


def _tips_app(fake_tips_engine: _FakeTipsEngine, monkeypatch) -> FastAPI:
    app = FastAPI()
    app.include_router(tips_router.router)
    for path in ("/tips", "/tips/categories", "/tips/category/{category}", "/tips/project/{project}"):
        auth_dep = _permission_dependency_for(tips_router.router, path, "GET")
        app.dependency_overrides[auth_dep] = lambda: AuthResult(
            authenticated=True,
            tenant_id="tenant-tips",
            permissions=["read"],
        )
    app.dependency_overrides[get_engine] = lambda: object()
    monkeypatch.setattr(tips_router, "_get_tips_engine", lambda engine: fake_tips_engine)
    return app


def test_get_tips_awaits_random_and_all_tips(monkeypatch) -> None:
    fake_tips_engine = _FakeTipsEngine()
    app = _tips_app(fake_tips_engine, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/tips?count=2&lang=en")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["total_available"] == 3
    assert fake_tips_engine.random.await_count == 2
    fake_tips_engine.all_tips.assert_awaited_once_with(lang="en")


def test_list_tip_categories_awaits_all_tips(monkeypatch) -> None:
    fake_tips_engine = _FakeTipsEngine()
    app = _tips_app(fake_tips_engine, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/tips/categories?lang=en")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["categories"]["cortex"] == 2
    fake_tips_engine.all_tips.assert_awaited_once_with(lang="en")


def test_get_tips_by_category_awaits_async_engine(monkeypatch) -> None:
    fake_tips_engine = _FakeTipsEngine()
    app = _tips_app(fake_tips_engine, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/tips/category/cortex?lang=en&limit=2")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    fake_tips_engine.for_category.assert_awaited_once_with("cortex", lang="en", limit=2)


def test_get_tips_by_project_awaits_async_engine(monkeypatch) -> None:
    fake_tips_engine = _FakeTipsEngine()
    app = _tips_app(fake_tips_engine, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/tips/project/alpha?lang=en&limit=2")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    fake_tips_engine.for_project.assert_awaited_once_with("alpha", lang="en", limit=2)
