from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.extensions.continual_learning import MicroUpdatePlan, MixedBatch
from cortex.routes import memories as memories_router
from cortex.search.models import SearchResult as InternalSearchResult


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeMemoriesAliasEngine:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.chain_calls: list[dict[str, object]] = []
        self.memory = _FakeContinualRouteManager()

    async def search(self, **kwargs) -> list[InternalSearchResult]:
        self.search_calls.append(kwargs)
        return [
            InternalSearchResult(
                fact_id=7,
                content="legacy memory search result",
                project="alpha",
                fact_type="decision",
                confidence="C4",
                valid_from="2026-04-07T00:00:00Z",
                valid_until=None,
                tags=["legacy", "alias"],
                created_at="2026-04-07T00:00:00Z",
                updated_at="2026-04-07T00:00:01Z",
                score=0.88,
                meta={"source": "compat"},
                tx_id=11,
                hash="hash-7",
                graph_context={"graph": {"nodes": []}},
            )
        ]

    async def get_causal_chain(self, **kwargs) -> list[dict[str, object]]:
        self.chain_calls.append(kwargs)
        return [{"id": 7, "project": "alpha"}]


class _FakeContinualRouteManager:
    def __init__(self) -> None:
        self.status_calls: list[dict[str, object]] = []
        self.plan_calls: list[dict[str, object]] = []
        self.execute_calls: list[dict[str, object]] = []
        self.forget_calls: list[dict[str, object]] = []

    async def continual_learning_status(self, **kwargs) -> dict[str, object]:
        self.status_calls.append(kwargs)
        return {"enabled": True, "tenant_id": kwargs["tenant_id"], "domain": kwargs.get("domain")}

    async def plan_continual_update(self, **kwargs) -> dict[str, object]:
        self.plan_calls.append(kwargs)
        return MicroUpdatePlan(
            tenant_id=str(kwargs["tenant_id"]),
            domain=str(kwargs["domain"]),
            adapter_id="lora:test",
            learning_rate=5e-5,
            risk_score=0.2,
            batch=MixedBatch(),
        )

    async def execute_continual_update(self, **kwargs) -> dict[str, object]:
        self.execute_calls.append(kwargs)
        return {
            "committed": True,
            "plan": {"tenant_id": kwargs["tenant_id"], "domain": kwargs["domain"]},
        }

    async def forget_continual_memory(self, **kwargs) -> dict[str, object]:
        self.forget_calls.append(kwargs)
        return {"deleted_exp_ids": ["exp-1"], "query": kwargs["query"]}


def _build_app(fake_engine: _FakeMemoriesAliasEngine) -> FastAPI:
    app = FastAPI()
    app.include_router(memories_router.router)
    auth_override = lambda: AuthResult(  # noqa: E731
        authenticated=True,
        tenant_id="tenant-memories",
        permissions=["read", "write"],
    )
    search_auth_dep = _dependency_for(
        "/v1/memories/search",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/search", "POST"),
    )
    chain_auth_dep = _dependency_for(
        "/v1/memories/{memory_id}/chain",
        "GET",
        _route_by_path(memories_router.router, "/v1/memories/{memory_id}/chain", "GET"),
    )
    status_auth_dep = _dependency_for(
        "/v1/memories/continual/status",
        "GET",
        _route_by_path(memories_router.router, "/v1/memories/continual/status", "GET"),
    )
    plan_auth_dep = _dependency_for(
        "/v1/memories/continual/plan",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/continual/plan", "POST"),
    )
    forget_auth_dep = _dependency_for(
        "/v1/memories/continual/forget",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/continual/forget", "POST"),
    )
    execute_auth_dep = _dependency_for(
        "/v1/memories/continual/execute",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/continual/execute", "POST"),
    )
    app.dependency_overrides[search_auth_dep] = auth_override
    app.dependency_overrides[chain_auth_dep] = auth_override
    app.dependency_overrides[status_auth_dep] = auth_override
    app.dependency_overrides[plan_auth_dep] = auth_override
    app.dependency_overrides[forget_auth_dep] = auth_override
    app.dependency_overrides[execute_auth_dep] = auth_override
    app.dependency_overrides[get_async_engine] = lambda: fake_engine
    return app


def test_memories_search_delegates_to_canonical_search_contract() -> None:
    fake_engine = _FakeMemoriesAliasEngine()
    app = _build_app(fake_engine)

    payload = {
        "query": "legacy alias",
        "k": 4,
        "project": "alpha",
        "tags": ["legacy", "alias"],
        "as_of": "2026-04-07T00:00:00Z",
    }

    with TestClient(app) as client:
        response = client.post("/v1/memories/search", json=payload)

    assert response.status_code == 200
    assert fake_engine.search_calls == [
        {
            "query": "legacy alias",
            "top_k": 4,
            "project": "alpha",
            "tenant_id": "tenant-memories",
            "as_of": "2026-04-07T00:00:00Z",
            "fact_type": None,
            "tags": ["legacy", "alias"],
            "graph_depth": 0,
            "include_graph": False,
        }
    ]
    assert response.json() == [
        {
            "id": 7,
            "project": "alpha",
            "content": "legacy memory search result",
            "type": "decision",
            "tags": ["legacy", "alias"],
            "confidence": "C3",
            "source": None,
            "parent_decision_id": None,
            "created_at": "2026-04-07T00:00:00Z",
            "updated_at": "2026-04-07T00:00:01Z",
            "hash": "hash-7",
            "score": 0.88,
        }
    ]


def test_memories_chain_delegates_tenant_scoped_canonical_handler() -> None:
    fake_engine = _FakeMemoriesAliasEngine()
    app = _build_app(fake_engine)

    with TestClient(app) as client:
        response = client.get("/v1/memories/7/chain?direction=up&max_depth=3")

    assert response.status_code == 200
    assert response.json() == [{"id": 7, "project": "alpha"}]
    assert fake_engine.chain_calls == [
        {
            "fact_id": 7,
            "direction": "up",
            "max_depth": 3,
            "tenant_id": "tenant-memories",
        }
    ]


def test_memories_continual_routes_delegate_to_manager() -> None:
    fake_engine = _FakeMemoriesAliasEngine()
    app = _build_app(fake_engine)

    with TestClient(app) as client:
        status_response = client.get("/v1/memories/continual/status?domain=support")
        plan_response = client.post(
            "/v1/memories/continual/plan",
            json={"domain": "support", "policy_violation": True},
        )
        execute_response = client.post(
            "/v1/memories/continual/execute",
            json={
                "domain": "support",
                "policy_violation": True,
                "critical_domains": ["support"],
            },
        )
        forget_response = client.post(
            "/v1/memories/continual/forget",
            json={"user_id": "user-1", "query": "secret"},
        )

    assert status_response.status_code == 200
    assert status_response.json() == {
        "enabled": True,
        "tenant_id": "tenant-memories",
        "domain": "support",
    }
    assert plan_response.status_code == 200
    assert plan_response.json()["adapter_id"] == "lora:test"
    assert execute_response.status_code == 200
    assert execute_response.json() == {
        "committed": True,
        "plan": {"tenant_id": "tenant-memories", "domain": "support"},
    }
    assert forget_response.status_code == 200
    assert forget_response.json() == {"deleted_exp_ids": ["exp-1"], "query": "secret"}
    assert fake_engine.memory.status_calls == [
        {"tenant_id": "tenant-memories", "domain": "support"}
    ]
    assert fake_engine.memory.plan_calls == [
        {"tenant_id": "tenant-memories", "domain": "support", "policy_violation": True}
    ]
    assert fake_engine.memory.execute_calls == [
        {
            "tenant_id": "tenant-memories",
            "domain": "support",
            "policy_violation": True,
            "critical_domains": ["support"],
        }
    ]
    assert fake_engine.memory.forget_calls == [
        {"tenant_id": "tenant-memories", "user_id": "user-1", "query": "secret"}
    ]
