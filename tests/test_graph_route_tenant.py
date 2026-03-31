from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes import graph as graph_routes


class _StubSession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class StubEngine:
    def session(self):
        return _StubSession()


def _client(auth_result: AuthResult) -> TestClient:
    app = FastAPI()
    app.include_router(graph_routes.router)
    app.dependency_overrides[require_auth] = lambda: auth_result
    app.dependency_overrides[graph_routes.get_engine] = lambda: StubEngine()
    return TestClient(app)


def test_graph_all_scopes_to_authenticated_tenant(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_get_graph(conn, project=None, limit=50, tenant_id="default") -> dict:
        calls.append({"project": project, "limit": limit, "tenant_id": tenant_id})
        return {"entities": [], "relationships": [], "stats": {"total_entities": 0}}

    monkeypatch.setattr(graph_routes, "_get_graph", fake_get_graph)
    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-graph",
            permissions=["read"],
            key_name="graph-key",
        )
    )

    response = client.get("/v1/graph")

    assert response.status_code == 200
    assert calls == [{"project": None, "limit": 50, "tenant_id": "tenant-graph"}]


def test_graph_project_allows_projects_distinct_from_tenant_id(monkeypatch) -> None:
    calls: list[dict] = []

    async def fake_get_graph(conn, project=None, limit=50, tenant_id="default") -> dict:
        calls.append({"project": project, "limit": limit, "tenant_id": tenant_id})
        return {"entities": [{"id": 1, "project": project}], "relationships": [], "stats": {}}

    monkeypatch.setattr(graph_routes, "_get_graph", fake_get_graph)
    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-graph",
            permissions=["read"],
            key_name="graph-key",
        )
    )

    response = client.get("/v1/graph/project-alpha", params={"limit": 25})

    assert response.status_code == 200
    assert response.json()["entities"][0]["project"] == "project-alpha"
    assert calls == [{"project": "project-alpha", "limit": 25, "tenant_id": "tenant-graph"}]
