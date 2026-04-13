from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cortex.auth.models import AuthResult
from cortex.routes import tips as tips_router
from cortex.services.tips_engine import Tip, TipCategory


def _route_by_path(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _dependency_by_name(route: APIRoute, name: str):
    for dependency in route.dependant.dependencies:
        if getattr(dependency.call, "__name__", "") == name:
            return dependency.call
    raise AssertionError(f"Dependency not found: {name}")


class _TipsEngineStub:
    def __init__(self) -> None:
        self.count = 4
        self.random = Mock()
        self.all_tips = Mock()
        self.for_category = Mock()
        self.for_project = Mock()


@pytest.fixture
def tips_client(monkeypatch):
    engine = AsyncMock()
    tips_engine = _TipsEngineStub()
    app = FastAPI()
    app.include_router(tips_router.router)

    for path in ["/tips", "/tips/categories", "/tips/category/{category}", "/tips/project/{project}"]:
        route = _route_by_path(tips_router.router, path, "GET")
        app.dependency_overrides[_dependency_by_name(route, "checker")] = lambda: AuthResult(
            authenticated=True,
            tenant_id="tenant-alpha",
            permissions=["read"],
        )
        app.dependency_overrides[_dependency_by_name(route, "get_engine")] = lambda: engine

    monkeypatch.setattr(tips_router, "_tips_engine", None)
    monkeypatch.setattr(tips_router, "_get_tips_engine", lambda _engine: tips_engine)

    client = TestClient(app)
    try:
        yield client, tips_engine
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_tips_contract_stays_stable(tips_client) -> None:
    client, tips_engine = tips_client
    tips_engine.random.side_effect = [
        Tip(id="tip-1", content="Primer consejo", category=TipCategory.WORKFLOW, lang="es"),
        Tip(id="tip-2", content="Segundo consejo", category=TipCategory.SECURITY, lang="es"),
    ]

    response = client.get("/tips", params={"count": 2, "lang": "es"})

    assert response.status_code == 200
    assert response.json() == {
        "tips": [
            {
                "id": "tip-1",
                "content": "Primer consejo",
                "category": "workflow",
                "lang": "es",
                "source": "static",
                "project": None,
                "relevance": 1.0,
                "formatted": "\U0001F4A1 [workflow] Primer consejo",
            },
            {
                "id": "tip-2",
                "content": "Segundo consejo",
                "category": "security",
                "lang": "es",
                "source": "static",
                "project": None,
                "relevance": 1.0,
                "formatted": "\U0001F4A1 [security] Segundo consejo",
            },
        ],
        "count": 2,
        "lang": "es",
        "category": None,
        "project": None,
        "total_available": 4,
    }


def test_list_tip_categories_contract_stays_stable(tips_client) -> None:
    client, tips_engine = tips_client
    tips_engine.all_tips.return_value = [
        Tip(id="tip-1", content="A", category=TipCategory.WORKFLOW, lang="en"),
        Tip(id="tip-2", content="B", category=TipCategory.WORKFLOW, lang="en"),
        Tip(id="tip-3", content="C", category=TipCategory.SECURITY, lang="en"),
    ]

    response = client.get("/tips/categories", params={"lang": "en"})

    assert response.status_code == 200
    assert response.json() == {
        "categories": {"workflow": 2, "security": 1},
        "total": 3,
        "lang": "en",
    }


def test_get_tips_by_category_contract_stays_stable(tips_client) -> None:
    client, tips_engine = tips_client
    tips_engine.for_category.return_value = [
        Tip(id="tip-4", content="Arquitectura", category=TipCategory.ARCHITECTURE, lang="es")
    ]

    response = client.get("/tips/category/architecture", params={"lang": "es", "limit": 1})

    assert response.status_code == 200
    assert response.json() == {
        "tips": [
            {
                "id": "tip-4",
                "content": "Arquitectura",
                "category": "architecture",
                "lang": "es",
                "source": "static",
                "project": None,
                "relevance": 1.0,
                "formatted": "\U0001F4A1 [architecture] Arquitectura",
            }
        ],
        "count": 1,
        "lang": "es",
        "category": "architecture",
        "project": None,
        "total_available": None,
    }


def test_get_tips_by_project_contract_stays_stable(tips_client) -> None:
    client, tips_engine = tips_client
    tips_engine.for_project.return_value = [
        Tip(
            id="tip-5",
            content="Consejo de proyecto",
            category=TipCategory.MEMORY,
            lang="es",
            source="memory",
            project="proj-alpha",
            relevance=0.8,
        )
    ]

    response = client.get("/tips/project/proj-alpha", params={"lang": "es", "limit": 1})

    assert response.status_code == 200
    assert response.json() == {
        "tips": [
            {
                "id": "tip-5",
                "content": "Consejo de proyecto",
                "category": "memory",
                "lang": "es",
                "source": "memory",
                "project": "proj-alpha",
                "relevance": 0.8,
                "formatted": "\U0001F4A1 [memory] Consejo de proyecto",
            }
        ],
        "count": 1,
        "lang": "es",
        "category": None,
        "project": "proj-alpha",
        "total_available": None,
    }
