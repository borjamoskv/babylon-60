from __future__ import annotations

import json
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.routes import ask as ask_router
from cortex.api.deps import get_async_engine
from cortex.extensions.llm.router import IntentProfile


def _dependency_for(path: str, method: str, app_route: APIRoute) -> callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class FakeFact:
    def __init__(self, fact_id: int, content: str, score: float, project: str) -> None:
        self.fact_id = fact_id
        self.content = content
        self.score = score
        self.project = project


class FakeEngine:
    async def search(self, query: str, top_k: int, project: str | None, tenant_id: str):
        return [
            FakeFact(1, "Sovereign intelligence preserves physical exergy.", 0.99, "cortex"),
            FakeFact(
                2, "Byzantine boundaries protect cryptographic ledger integrity.", 0.95, "cortex"
            ),
        ]


class FakeLLMManager:
    def __init__(self, should_fail: bool, error_msg: str = "") -> None:
        self.available = True
        self.should_fail = should_fail
        self.error_msg = error_msg
        self.provider_name = "test-provider"
        self.model_name = "test-model"

    async def complete(
        self, prompt: str, system: str, temperature: float, max_tokens: int, intent: IntentProfile
    ) -> str | None:
        if self.should_fail:
            raise RuntimeError(self.error_msg)
        return "Validated sovereign logic response."

    async def stream(
        self, prompt: str, system: str, temperature: float, max_tokens: int, intent: IntentProfile
    ):
        if self.should_fail:
            raise RuntimeError(self.error_msg)
        yield "Token 1"
        yield "Token 2"


@pytest.mark.asyncio
async def test_ask_cortex_capacity_exhaustion_503(monkeypatch) -> None:
    fake_llm = FakeLLMManager(
        should_fail=True, error_msg="Model capacity exhausted: 503 Overloaded"
    )
    monkeypatch.setattr(ask_router, "_llm_manager", fake_llm)

    app = FastAPI()
    app.include_router(ask_router.router)
    auth_dep = _dependency_for(
        "/v1/ask",
        "POST",
        _route_by_path(ask_router.router, "/v1/ask", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-test",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.post(
            "/v1/ask",
            json={"query": "What is the truth of the system?", "k": 2},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "All LLM capacity exhausted. Please try again later."


@pytest.mark.asyncio
async def test_ask_cortex_generic_llm_error_502(monkeypatch) -> None:
    fake_llm = FakeLLMManager(should_fail=True, error_msg="Connection timed out")
    monkeypatch.setattr(ask_router, "_llm_manager", fake_llm)

    app = FastAPI()
    app.include_router(ask_router.router)
    auth_dep = _dependency_for(
        "/v1/ask",
        "POST",
        _route_by_path(ask_router.router, "/v1/ask", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-test",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.post(
            "/v1/ask",
            json={"query": "What is the truth of the system?", "k": 2},
        )

    assert response.status_code == 502
    assert "LLM provider error: Connection timed out" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ask_stream_capacity_exhaustion_503(monkeypatch) -> None:
    fake_llm = FakeLLMManager(
        should_fail=True, error_msg="Model capacity exhausted: 503 Overloaded"
    )
    monkeypatch.setattr(ask_router, "_llm_manager", fake_llm)

    app = FastAPI()
    app.include_router(ask_router.router)
    auth_dep = _dependency_for(
        "/v1/ask/stream",
        "POST",
        _route_by_path(ask_router.router, "/v1/ask/stream", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-test",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.post(
            "/v1/ask/stream",
            json={"query": "What is the truth of the system?", "k": 2},
        )

    assert response.status_code == 200
    lines = response.text.split("\n")
    events = [line for line in lines if line.startswith("data: ")]

    # The first event is the sources metadata
    assert len(events) >= 2
    sources_event = json.loads(events[0][6:])
    assert sources_event["type"] == "sources"

    # The second event should carry the capacity exhaustion error message
    error_event = json.loads(events[1][6:])
    assert error_event["type"] == "error"
    assert error_event["data"] == "All LLM capacity exhausted. Please try again later."


@pytest.mark.asyncio
async def test_ask_stream_generic_llm_error_502(monkeypatch) -> None:
    fake_llm = FakeLLMManager(should_fail=True, error_msg="Authentication failed")
    monkeypatch.setattr(ask_router, "_llm_manager", fake_llm)

    app = FastAPI()
    app.include_router(ask_router.router)
    auth_dep = _dependency_for(
        "/v1/ask/stream",
        "POST",
        _route_by_path(ask_router.router, "/v1/ask/stream", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-test",
        permissions=["read"],
    )
    app.dependency_overrides[get_async_engine] = lambda: FakeEngine()

    with TestClient(app) as client:
        response = client.post(
            "/v1/ask/stream",
            json={"query": "What is the truth of the system?", "k": 2},
        )

    assert response.status_code == 200
    lines = response.text.split("\n")
    events = [line for line in lines if line.startswith("data: ")]

    assert len(events) >= 2
    error_event = json.loads(events[1][6:])
    assert error_event["type"] == "error"
    assert "LLM provider error: Authentication failed" in error_event["data"]
