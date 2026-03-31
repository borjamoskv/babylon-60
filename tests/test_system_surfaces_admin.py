from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes import daemon as daemon_routes
from cortex.routes import notebooklm as notebooklm_routes
from cortex.routes import observatory as observatory_routes


def _client(auth_result: AuthResult) -> TestClient:
    app = FastAPI()
    app.include_router(observatory_routes.router)
    app.include_router(daemon_routes.router)
    app.include_router(notebooklm_routes.router)
    app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def _read_auth() -> AuthResult:
    return AuthResult(
        authenticated=True,
        tenant_id="tenant-surface",
        permissions=["read", "write"],
        key_name="reader-key",
    )


def _admin_auth() -> AuthResult:
    return AuthResult(
        authenticated=True,
        tenant_id="tenant-surface",
        permissions=["read", "write", "admin"],
        key_name="admin-key",
    )


def test_observatory_requires_admin(monkeypatch) -> None:
    monkeypatch.setattr(observatory_routes, "_get_daemon_status", lambda: {"status": "ok"})
    monkeypatch.setattr(observatory_routes, "_get_dependency_health", lambda: {"status": "ok"})
    monkeypatch.setattr(observatory_routes, "_get_effectiveness", lambda: {"tenant": {"score": 1}})
    monkeypatch.setattr(observatory_routes, "_get_evolution_status", lambda: {"status": "idle"})
    monkeypatch.setattr(observatory_routes, "_get_recent_decisions", lambda: [])

    denied = _client(_read_auth()).get("/v1/observatory")
    assert denied.status_code == 403

    allowed = _client(_admin_auth()).get("/v1/observatory")
    assert allowed.status_code == 200
    assert allowed.json()["daemon"]["status"] == "ok"


def test_daemon_status_requires_admin(monkeypatch) -> None:
    fake_daemon_module = SimpleNamespace(
        MoskvDaemon=SimpleNamespace(load_status=lambda: {"status": "green"})
    )
    monkeypatch.setitem(sys.modules, "cortex.extensions.daemon", fake_daemon_module)

    denied = _client(_read_auth()).get("/v1/daemon/status")
    assert denied.status_code == 403

    allowed = _client(_admin_auth()).get("/v1/daemon/status")
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "green"


def test_notebooklm_status_requires_admin(monkeypatch, tmp_path: Path) -> None:
    digest = tmp_path / "digest.md"
    digest.write_text("digest", encoding="utf-8")
    domains = tmp_path / "domains"
    domains.mkdir()
    (domains / "ops.md").write_text("ops", encoding="utf-8")

    fake_module = SimpleNamespace(
        CLOUD_PROVIDERS={"drive": [tmp_path / "cloud" / "notebooklm"]},
        DIGEST_FILE=digest,
        DOMAINS_DIR=domains,
        NotebookLMService=None,
    )
    monkeypatch.setitem(sys.modules, "cortex.services.notebooklm", fake_module)

    denied = _client(_read_auth()).get("/v1/notebooklm/status")
    assert denied.status_code == 403

    allowed = _client(_admin_auth()).get("/v1/notebooklm/status")
    assert allowed.status_code == 200
    assert allowed.json()["digest"]["exists"] is True


def test_notebooklm_digest_requires_admin(monkeypatch, tmp_path: Path) -> None:
    class FakeNotebookLMService:
        def __init__(self, db_path: str) -> None:
            self.db_path = db_path

        async def generate_digest(self, project=None) -> str:
            return "digest-body"

    fake_module = SimpleNamespace(NotebookLMService=FakeNotebookLMService)
    monkeypatch.setitem(sys.modules, "cortex.services.notebooklm", fake_module)
    monkeypatch.chdir(tmp_path)

    denied = _client(_read_auth()).post(
        "/v1/notebooklm/digest",
        params={"output": "tenant_digest.md"},
    )
    assert denied.status_code == 403

    allowed = _client(_admin_auth()).post(
        "/v1/notebooklm/digest",
        params={"output": "tenant_digest.md"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["facts_count"] == 0
