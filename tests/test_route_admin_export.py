from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.routes import admin as admin_router


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


class _Fact:
    def __init__(self, project: str, content: str) -> None:
        self.project = project
        self.content = content

    def to_dict(self) -> dict[str, object]:
        return {
            "id": 1,
            "project": self.project,
            "content": self.content,
            "fact_type": "knowledge",
            "tags": ["contract"],
            "confidence": "C3",
            "valid_from": None,
            "valid_until": None,
            "source": "test",
        }


class _Engine:
    def search(self, *, project: str, limit: int) -> list[_Fact]:
        assert project == "tenant-alpha"
        assert limit == admin_router._MAX_EXPORT_FACTS
        return [_Fact(project, "fact exportable")]


def test_export_project_contract_stays_stable(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    app.include_router(admin_router.router)
    route = _route_by_path(admin_router.router, "/v1/projects/{project}/export", "GET")
    auth_dep = route.dependant.dependencies[2].call
    engine_dep = route.dependant.dependencies[3].call
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-alpha",
        permissions=["admin"],
    )
    app.dependency_overrides[engine_dep] = lambda: _Engine()

    with TestClient(app) as client:
        response = client.get("/v1/projects/tenant-alpha/export")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["project"] == "tenant-alpha"
    artifact = Path(body["artifact"])
    assert artifact.name == "tenant-alpha_export.json"
    assert json.loads(artifact.read_text(encoding="utf-8")) == [
        {
            "id": 1,
            "project": "tenant-alpha",
            "content": "fact exportable",
            "fact_type": "knowledge",
            "tags": ["contract"],
            "confidence": "C3",
            "valid_from": None,
            "valid_until": None,
            "source": "test",
        }
    ]
    assert isinstance(body["message"], str) and body["message"]


def test_export_project_rejects_non_json_format(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    app.include_router(admin_router.router)
    route = _route_by_path(admin_router.router, "/v1/projects/{project}/export", "GET")
    auth_dep = route.dependant.dependencies[2].call
    engine_dep = route.dependant.dependencies[3].call
    app.dependency_overrides[auth_dep] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-alpha",
        permissions=["admin"],
    )
    app.dependency_overrides[engine_dep] = lambda: _Engine()

    with TestClient(app) as client:
        response = client.get("/v1/projects/tenant-alpha/export", params={"format": "csv"})

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str) and response.json()["detail"]
