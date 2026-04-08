from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
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
    app.dependency_overrides[search_auth_dep] = auth_override
    app.dependency_overrides[chain_auth_dep] = auth_override
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
