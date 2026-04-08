from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import search as search_router
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


class _FakeSearchEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(self, **kwargs) -> list[InternalSearchResult]:
        self.calls.append(kwargs)
        return [
            InternalSearchResult(
                fact_id=42,
                content="search result",
                project="alpha",
                fact_type="decision",
                confidence="C4",
                valid_from="2026-04-04T00:00:00Z",
                valid_until=None,
                tags=["policy", "edge"],
                created_at="2026-04-04T00:00:00Z",
                updated_at="2026-04-04T00:00:01Z",
                score=0.91,
                meta={"source": "unit-test"},
                tx_id=123,
                hash="abc123",
                graph_context={"graph": {"nodes": [{"id": "n1"}]}, "seeds": ["n1"]},
            )
        ]


def _build_app(fake_engine: _FakeSearchEngine) -> FastAPI:
    app = FastAPI()
    app.include_router(search_router.router)
    auth_override = lambda: AuthResult(  # noqa: E731
        authenticated=True,
        tenant_id="tenant-search",
        permissions=["read"],
    )
    post_auth_dep = _dependency_for(
        "/v1/search",
        "POST",
        _route_by_path(search_router.router, "/v1/search", "POST"),
    )
    get_auth_dep = _dependency_for(
        "/v1/search",
        "GET",
        _route_by_path(search_router.router, "/v1/search", "GET"),
    )
    app.dependency_overrides[post_auth_dep] = auth_override
    app.dependency_overrides[get_auth_dep] = auth_override
    app.dependency_overrides[get_async_engine] = lambda: fake_engine
    return app


def test_search_post_propagates_filters_and_serializes_graph_context() -> None:
    fake_engine = _FakeSearchEngine()
    app = _build_app(fake_engine)

    payload = {
        "query": "graph integrity",
        "k": 7,
        "project": "alpha",
        "as_of": "2026-04-04T00:00:00Z",
        "fact_type": "decision",
        "tags": ["policy", "edge"],
        "graph_depth": 2,
        "include_graph": True,
    }

    with TestClient(app) as client:
        response = client.post("/v1/search", json=payload)

    assert response.status_code == 200
    assert fake_engine.calls == [
        {
            "query": "graph integrity",
            "top_k": 7,
            "project": "alpha",
            "tenant_id": "tenant-search",
            "as_of": "2026-04-04T00:00:00Z",
            "fact_type": "decision",
            "tags": ["policy", "edge"],
            "graph_depth": 2,
            "include_graph": True,
        }
    ]
    assert response.json() == [
        {
            "fact_id": 42,
            "project": "alpha",
            "content": "search result",
            "fact_type": "decision",
            "score": 0.91,
            "tags": ["policy", "edge"],
            "created_at": "2026-04-04T00:00:00Z",
            "updated_at": "2026-04-04T00:00:01Z",
            "meta": {"source": "unit-test"},
            "tx_id": 123,
            "hash": "abc123",
            "context": {"graph": {"nodes": [{"id": "n1"}]}, "seeds": ["n1"]},
        }
    ]


def test_search_get_accepts_filters_and_repeated_tags() -> None:
    fake_engine = _FakeSearchEngine()
    app = _build_app(fake_engine)

    params = [
        ("query", "graph integrity"),
        ("k", "3"),
        ("project", "alpha"),
        ("as_of", "2026-04-04T00:00:00Z"),
        ("fact_type", "decision"),
        ("tags", "policy"),
        ("tags", "edge"),
        ("graph_depth", "1"),
        ("include_graph", "true"),
    ]

    with TestClient(app) as client:
        response = client.get("/v1/search", params=params)

    assert response.status_code == 200
    assert fake_engine.calls == [
        {
            "query": "graph integrity",
            "top_k": 3,
            "project": "alpha",
            "tenant_id": "tenant-search",
            "as_of": "2026-04-04T00:00:00Z",
            "fact_type": "decision",
            "tags": ["policy", "edge"],
            "graph_depth": 1,
            "include_graph": True,
        }
    ]
    assert response.json()[0]["tx_id"] == 123
    assert response.json()[0]["context"] == {
        "graph": {"nodes": [{"id": "n1"}]},
        "seeds": ["n1"],
    }
