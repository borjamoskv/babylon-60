from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import cortex.auth.deps as auth_deps
from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import notch_ws, telemetry, topology_ws


class FakeAuthManager:
    async def authenticate_async(self, raw_key: str) -> AuthResult:
        if raw_key == "ctx_good":
            return AuthResult(
                authenticated=True,
                tenant_id="tenant-ws",
                permissions=["read"],
                key_name="ws-key",
            )
        if raw_key == "ctx_noread":
            return AuthResult(
                authenticated=True,
                tenant_id="tenant-ws",
                permissions=[],
                key_name="limited-key",
            )
        return AuthResult(authenticated=False, error="Invalid or revoked key")


class _FakeCursor:
    async def fetchone(self):
        return (0,)

    async def fetchall(self):
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeConn:
    async def execute(self, sql, params=None):
        return _FakeCursor()


class _FakeSession:
    async def __aenter__(self):
        return _FakeConn()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeAsyncEngine:
    def session(self):
        return _FakeSession()


def _client(monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(notch_ws.router)
    app.include_router(topology_ws.router)
    app.include_router(telemetry.router)
    app.dependency_overrides[get_async_engine] = lambda: FakeAsyncEngine()
    monkeypatch.setattr(auth_deps, "get_auth_manager", lambda: FakeAuthManager())
    return TestClient(app)


def test_notch_websocket_requires_auth(monkeypatch) -> None:
    client = _client(monkeypatch)

    try:
        with client.websocket_connect("/ws/notch"):
            raise AssertionError("Expected websocket handshake to be denied")
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
        assert exc.reason == "Authentication required"


def test_notch_websocket_allows_authorization_header(monkeypatch) -> None:
    client = _client(monkeypatch)

    with client.websocket_connect(
        "/ws/notch",
        headers={"Authorization": "Bearer ctx_good"},
    ) as websocket:
        assert notch_ws.notch_hub.client_count == 1
        websocket.send_text("pong")

    assert notch_ws.notch_hub.client_count == 0


def test_topology_websocket_accepts_api_key_query_param(monkeypatch) -> None:
    client = _client(monkeypatch)

    with client.websocket_connect("/ws/v1/topology?api_key=ctx_good") as websocket:
        assert len(topology_ws.topology_manager.active_connections) == 1
        websocket.send_text("{}")

    assert topology_ws.topology_manager.active_connections == []


def test_topology_websocket_rejects_missing_read_permission(monkeypatch) -> None:
    client = _client(monkeypatch)

    try:
        with client.websocket_connect("/ws/v1/topology?api_key=ctx_noread"):
            raise AssertionError("Expected websocket handshake to be denied")
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
        assert exc.reason == "Missing permission: read"


def test_telemetry_websocket_requires_auth(monkeypatch) -> None:
    client = _client(monkeypatch)

    try:
        with client.websocket_connect("/telemetry/ast-oracle"):
            raise AssertionError("Expected websocket handshake to be denied")
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
        assert exc.reason == "Authentication required"
