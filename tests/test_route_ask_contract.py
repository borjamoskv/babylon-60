from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.routes import ask as ask_router


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _dependencies_for(route: APIRoute) -> list[Callable]:
    return [dependency.call for dependency in route.dependant.dependencies]


class _FakeProvider:
    provider_name = "openai"
    model_name = "gpt-5.4"


class _FakeManager:
    available = True
    provider_name = "openai"
    provider = _FakeProvider()

    async def complete(self, **kwargs):
        return "Grounded answer [Fact #7]"

    async def stream(self, **kwargs):
        for chunk in ["Grounded ", "stream"]:
            yield chunk


def _make_auth() -> AuthResult:
    return AuthResult(
        authenticated=True,
        tenant_id="tenant-ask",
        permissions=["read"],
        key_name="ask-agent",
    )


def _make_engine():
    class _Engine:
        async def search(self, **kwargs):
            return [
                SimpleNamespace(
                    fact_id=7,
                    content="Alpha evidence block.",
                    score=0.91,
                    project="proj-alpha",
                )
            ]

    return _Engine()


def test_ask_endpoint_contract_stays_stable(monkeypatch) -> None:
    monkeypatch.setattr(ask_router, "_llm_manager", _FakeManager())

    app = FastAPI()
    app.include_router(ask_router.router)

    route = _route_by_path(ask_router.router, "/v1/ask", "POST")
    auth_dep, engine_dep = _dependencies_for(route)
    app.dependency_overrides[auth_dep] = _make_auth
    app.dependency_overrides[engine_dep] = _make_engine

    with TestClient(app) as client:
        response = client.post(
            "/v1/ask",
            json={"query": "What happened?", "project": "proj-alpha", "k": 1},
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Grounded answer [Fact #7]",
        "sources": [
            {
                "fact_id": 7,
                "content": "Alpha evidence block.",
                "score": 0.91,
                "project": "proj-alpha",
            }
        ],
        "model": "gpt-5.4",
        "provider": "openai",
        "facts_found": 1,
    }


def test_ask_stream_endpoint_contract_stays_stable(monkeypatch) -> None:
    monkeypatch.setattr(ask_router, "_llm_manager", _FakeManager())

    app = FastAPI()
    app.include_router(ask_router.router)

    route = _route_by_path(ask_router.router, "/v1/ask/stream", "POST")
    auth_dep, engine_dep = _dependencies_for(route)
    app.dependency_overrides[auth_dep] = _make_auth
    app.dependency_overrides[engine_dep] = _make_engine

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/v1/ask/stream",
            json={"query": "What happened?", "project": "proj-alpha", "k": 1},
        ) as response:
            body = "".join(response.iter_text())

    assert response.status_code == 200
    assert 'data: {"type": "sources", "data": [{"id": 7, "score": 0.91, "project": "proj-alpha"}]}' in body
    assert 'data: {"type": "token", "data": "Grounded "}' in body
    assert 'data: {"type": "token", "data": "stream"}' in body
    assert body.strip().endswith("data: [DONE]")
