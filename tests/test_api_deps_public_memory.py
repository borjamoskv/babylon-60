from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine, get_public_memory_service


class _FakeAsyncEngine:
    async def stats(self):
        return {
            "total_facts": 1,
            "active_facts": 1,
            "deprecated_facts": 0,
            "project_count": 1,
            "embeddings": 0,
            "transactions": 1,
            "db_size_mb": 0.1,
        }


def test_public_memory_service_dependency_respects_async_engine_override() -> None:
    app = FastAPI()

    @app.get("/status")
    async def status(service=Depends(get_public_memory_service)):
        status = await service.status()
        return {"total_facts": status.total_facts, "transactions": status.transactions}

    app.dependency_overrides[get_async_engine] = lambda: _FakeAsyncEngine()

    with TestClient(app) as client:
        response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"total_facts": 1, "transactions": 1}
