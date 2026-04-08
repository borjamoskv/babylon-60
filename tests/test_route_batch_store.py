from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.engine.storage_guard import GuardViolation
from cortex.routes import facts as facts_router
from cortex.routes import memories as memories_router


def _dependency_for(path: str, method: str, app_route: APIRoute) -> Callable:
    if app_route.path != path or method not in app_route.methods:
        raise ValueError(f"Unexpected route lookup: {app_route.path} {app_route.methods}")
    return app_route.dependant.dependencies[0].call


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _FakeBatchEngine:
    def __init__(self) -> None:
        self.store_many_calls: list[list[dict[str, object]]] = []

    async def store_many(self, facts: list[dict[str, object]]) -> list[int]:
        self.store_many_calls.append(facts)
        return list(range(1, len(facts) + 1))


class _FakeStoreEngine:
    def __init__(self) -> None:
        self.store_calls: list[dict[str, object]] = []

    async def store(self, **kwargs: object) -> int:
        self.store_calls.append(kwargs)
        return 42


class _GuardFailingBatchEngine:
    async def store_many(self, facts: list[dict[str, object]]) -> list[int]:
        raise GuardViolation("test_guard", "guard rejected batch")


class _GuardFailingStoreEngine:
    async def store(self, **kwargs: object) -> int:
        raise GuardViolation("test_guard", "guard rejected single memory")


def test_memories_store_uses_engine_store_once() -> None:
    fake_engine = _FakeStoreEngine()

    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-memories-store",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    payload = {
        "project": "alpha",
        "content": "Memory A long enough for validation.",
        "type": "knowledge",
        "tags": ["m"],
        "source": "test",
        "metadata": {"k": "v"},
        "parent_decision_id": 12,
    }

    with TestClient(app) as client:
        response = client.post("/v1/memories", json=payload)

    assert response.status_code == 200
    assert response.json() == {"id": 42, "project": "alpha", "status": "stored"}
    assert fake_engine.store_calls == [
        {
            "project": "alpha",
            "content": "Memory A long enough for validation.",
            "tenant_id": "tenant-memories-store",
            "fact_type": "knowledge",
            "tags": ["m"],
            "source": "test",
            "meta": {"k": "v"},
            "parent_decision_id": 12,
        }
    ]


def test_memories_store_maps_guard_rejection_to_400() -> None:
    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-memories-store",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _GuardFailingStoreEngine()

    payload = {
        "project": "alpha",
        "content": "Memory A long enough for validation.",
        "type": "knowledge",
        "tags": ["m"],
    }

    with TestClient(app) as client:
        response = client.post("/v1/memories", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "[test_guard] guard rejected single memory"}


def test_facts_batch_uses_store_many_once() -> None:
    fake_engine = _FakeBatchEngine()

    app = FastAPI()
    app.include_router(facts_router.router)
    auth_dep = _dependency_for(
        "/v1/facts/batch",
        "POST",
        _route_by_path(facts_router.router, "/v1/facts/batch", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-facts-batch",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    payload = {
        "facts": [
            {
                "project": "alpha",
                "content": "Fact A long enough for validation.",
                "fact_type": "knowledge",
                "tags": ["x"],
                "source": "test",
                "meta": {"k": "v"},
                "parent_decision_id": 10,
            },
            {
                "project": "beta",
                "content": "Fact B long enough for validation.",
                "fact_type": "decision",
                "tags": [],
                "source": None,
                "meta": None,
                "parent_decision_id": None,
            },
        ]
    }

    with TestClient(app) as client:
        response = client.post("/v1/facts/batch", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "stored": 2,
        "fact_ids": [1, 2],
        "errors": [],
        "total_requested": 2,
    }
    assert fake_engine.store_many_calls == [
        [
            {
                "project": "alpha",
                "content": "Fact A long enough for validation.",
                "tenant_id": "tenant-facts-batch",
                "fact_type": "knowledge",
                "tags": ["x"],
                "source": "test",
                "meta": {"k": "v"},
                "parent_decision_id": 10,
            },
            {
                "project": "beta",
                "content": "Fact B long enough for validation.",
                "tenant_id": "tenant-facts-batch",
                "fact_type": "decision",
                "tags": [],
                "source": None,
                "meta": {},
                "parent_decision_id": None,
            },
        ]
    ]


def test_memories_batch_uses_store_many_once() -> None:
    fake_engine = _FakeBatchEngine()

    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories/batch",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/batch", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-memories-batch",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: fake_engine

    payload = {
        "memories": [
            {
                "project": "alpha",
                "content": "Memory A long enough for validation.",
                "type": "knowledge",
                "tags": ["m"],
                "source": "test",
                "metadata": {"k": "v"},
                "parent_decision_id": 12,
            }
        ]
    }

    with TestClient(app) as client:
        response = client.post("/v1/memories/batch", json=payload)

    assert response.status_code == 200
    assert response.json() == {"stored": 1, "ids": [1], "errors": [], "total_requested": 1}
    assert fake_engine.store_many_calls == [
        [
            {
                "project": "alpha",
                "content": "Memory A long enough for validation.",
                "tenant_id": "tenant-memories-batch",
                "fact_type": "knowledge",
                "tags": ["m"],
                "source": "test",
                "meta": {"k": "v"},
                "parent_decision_id": 12,
            }
        ]
    ]


def test_memories_batch_maps_guard_rejection_to_400() -> None:
    app = FastAPI()
    app.include_router(memories_router.router)
    auth_dep = _dependency_for(
        "/v1/memories/batch",
        "POST",
        _route_by_path(memories_router.router, "/v1/memories/batch", "POST"),
    )
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-memories-batch",
        permissions=["write"],
    )
    app.dependency_overrides[get_async_engine] = lambda: _GuardFailingBatchEngine()

    payload = {
        "memories": [
            {
                "project": "alpha",
                "content": "Memory A long enough for validation.",
                "type": "knowledge",
                "tags": ["m"],
            }
        ]
    }

    with TestClient(app) as client:
        response = client.post("/v1/memories/batch", json=payload)

    assert response.status_code == 400
    assert response.json() == {"detail": "[test_guard] guard rejected batch"}
