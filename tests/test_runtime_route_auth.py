from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes.runtime import router
from cortex.types.models import RecoveryReport


def _client(
    auth_result: AuthResult | None = None,
    recovery_report: RecoveryReport | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.engine = SimpleNamespace(recovery_report=recovery_report)
    if auth_result is not None:
        app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def test_runtime_health_remains_public() -> None:
    client = _client()

    response = client.get("/v1/runtime/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_boot_recovery_requires_auth() -> None:
    client = _client()

    response = client.get("/v1/runtime/boot_recovery")

    assert response.status_code == 401


def test_boot_recovery_allows_authenticated_read() -> None:
    client = _client(
        auth_result=AuthResult(
            authenticated=True,
            tenant_id="tenant-runtime",
            permissions=["read"],
            key_name="runtime-key",
        ),
        recovery_report=RecoveryReport(
            status="recovered",
            recovered_items=3,
            failed_items=1,
            last_checkpoint_id="ckpt-7",
            warnings=["index repaired"],
        ),
    )

    response = client.get("/v1/runtime/boot_recovery")

    assert response.status_code == 200
    assert response.json()["status"] == "recovered"
    assert response.json()["last_checkpoint_id"] == "ckpt-7"
