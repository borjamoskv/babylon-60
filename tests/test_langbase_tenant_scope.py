from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.extensions.langbase.pipe import run_with_cortex_context
from cortex.extensions.langbase.sync import sync_to_langbase
from cortex.routes import langbase as langbase_routes


class _FakeLangbaseClient:
    def __init__(self) -> None:
        self.closed = False
        self.uploads: list[dict] = []

    async def run_pipe(self, **kwargs) -> dict:
        return {"completion": "ok", "threadId": kwargs.get("thread_id")}

    async def create_memory(self, **kwargs) -> None:
        return None

    async def upload_document(self, **kwargs) -> None:
        self.uploads.append(kwargs)

    async def close(self) -> None:
        self.closed = True


class _FakeFact:
    def __init__(self) -> None:
        self.id = 7
        self.project = "project-alpha"
        self.content = "remember this"
        self.fact_type = "knowledge"
        self.confidence = "verified"
        self.tags = ["langbase"]
        self.created_at = "2026-03-31T00:00:00Z"


class _RecordingEngine:
    def __init__(self) -> None:
        self.search_calls: list[dict] = []
        self.recall_calls: list[dict] = []

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return []

    async def recall(self, **kwargs):
        self.recall_calls.append(kwargs)
        return []


class _RouteEngine:
    pass


def _client(auth_result: AuthResult) -> TestClient:
    app = FastAPI()
    app.include_router(langbase_routes.router)
    app.dependency_overrides[require_auth] = lambda: auth_result
    app.dependency_overrides[get_async_engine] = lambda: _RouteEngine()
    return TestClient(app)


@pytest.mark.asyncio
async def test_run_with_cortex_context_passes_tenant_id_to_search() -> None:
    client = _FakeLangbaseClient()
    engine = _RecordingEngine()

    result = await run_with_cortex_context(
        client=client,
        engine=engine,
        pipe_name="support-bot",
        query="latest status",
        tenant_id="tenant-langbase",
        project="project-alpha",
        top_k=4,
    )

    assert result["facts_used"] == 0
    assert engine.search_calls == [
        {
            "query": "latest status",
            "tenant_id": "tenant-langbase",
            "top_k": 4,
            "project": "project-alpha",
        }
    ]


@pytest.mark.asyncio
async def test_sync_to_langbase_passes_tenant_id_to_recall() -> None:
    client = _FakeLangbaseClient()
    engine = _RecordingEngine()

    result = await sync_to_langbase(
        client=client,
        engine=engine,
        project="project-alpha",
        tenant_id="tenant-langbase",
        limit=12,
    )

    assert result["synced"] == 0
    assert engine.recall_calls == [
        {
            "project": "project-alpha",
            "limit": 12,
            "tenant_id": "tenant-langbase",
        }
    ]


def test_langbase_pipe_run_forwards_project_and_tenant_scope(monkeypatch) -> None:
    captured: list[dict] = []
    fake_client = _FakeLangbaseClient()

    async def fake_run_with_cortex_context(**kwargs) -> dict:
        captured.append(kwargs)
        return {"completion": "ok", "facts_used": 0, "sources": [], "thread_id": None}

    monkeypatch.setattr(langbase_routes, "_get_client", lambda: fake_client)
    monkeypatch.setattr(langbase_routes, "run_with_cortex_context", fake_run_with_cortex_context)

    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-langbase",
            permissions=["read", "write"],
            key_name="langbase-key",
        )
    )

    response = client.post(
        "/v1/langbase/pipe/run",
        json={
            "pipe_name": "support-bot",
            "query": "latest status",
            "project": "project-alpha",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    assert captured[0]["tenant_id"] == "tenant-langbase"
    assert captured[0]["project"] == "project-alpha"


def test_langbase_sync_allows_non_tenant_named_project_when_tenant_is_passed(monkeypatch) -> None:
    captured: list[dict] = []
    fake_client = _FakeLangbaseClient()

    async def fake_sync_to_langbase(**kwargs) -> dict:
        captured.append(kwargs)
        return {"synced": 0, "errors": 0, "memory": "cortex-project-alpha"}

    monkeypatch.setattr(langbase_routes, "_get_client", lambda: fake_client)
    monkeypatch.setattr(langbase_routes, "sync_to_langbase", fake_sync_to_langbase)

    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-langbase",
            permissions=["read", "write"],
            key_name="langbase-key",
        )
    )

    response = client.post(
        "/v1/langbase/sync",
        json={"project": "project-alpha", "limit": 25},
    )

    assert response.status_code == 200
    assert captured[0]["tenant_id"] == "tenant-langbase"
    assert captured[0]["project"] == "project-alpha"
