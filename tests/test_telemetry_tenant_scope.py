from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.websockets import WebSocketDisconnect

from cortex.auth.models import AuthResult
from cortex.routes import telemetry


class _FakeCursor:
    def __init__(self, rows=None, one=(0,)) -> None:
        self._rows = rows or []
        self._one = one

    async def fetchall(self):
        return self._rows

    async def fetchone(self):
        return self._one

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _QueryConn:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple]] = []

    async def execute(self, sql, params):
        self.calls.append((sql, params))
        return _FakeCursor(rows=self.rows)


class _Session:
    def __init__(self, conn) -> None:
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _QueryEngine:
    def __init__(self, conn) -> None:
        self.conn = conn

    def session(self):
        return _Session(self.conn)


@pytest.mark.asyncio
async def test_query_new_facts_filters_by_tenant() -> None:
    conn = _QueryConn(rows=[(8, "delta", '{"source":"ws"}')])
    engine = _QueryEngine(conn)

    max_id, results = await telemetry.query_new_facts(
        engine,
        last_id=5,
        fact_type="human_mutation",
        tenant_id="tenant-telemetry",
    )

    assert max_id == 8
    assert results == [{"fact_id": 8, "content": "delta", "meta": {"source": "ws"}}]
    assert conn.calls == [
        (
            """
            SELECT id, content, meta 
            FROM facts 
            WHERE tenant_id = ? AND fact_type = ? AND id > ? 
            ORDER BY id ASC
        """,
            ("tenant-telemetry", "human_mutation", 5),
        )
    ]


class _RouteConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def execute(self, sql, params):
        self.calls.append((sql, params))
        return _FakeCursor(one=(15,))


class _RouteEngine:
    def __init__(self, conn) -> None:
        self.conn = conn

    def session(self):
        return _Session(self.conn)


class _FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_ast_oracle_uses_authenticated_tenant_scope(monkeypatch) -> None:
    conn = _RouteConn()
    engine = _RouteEngine(conn)
    websocket = _FakeWebSocket()
    captured: list[tuple[int, str, str]] = []

    async def fake_query_new_facts(engine_arg, last_id, fact_type, tenant_id):
        captured.append((last_id, fact_type, tenant_id))
        raise WebSocketDisconnect(code=1000)

    monkeypatch.setattr(telemetry, "query_new_facts", fake_query_new_facts)

    await telemetry.ast_oracle_ws(
        websocket,
        AuthResult(
            authenticated=True,
            tenant_id="tenant-telemetry",
            permissions=["read"],
            key_name="telemetry-key",
        ),
        engine,
    )

    assert websocket.accepted is True
    assert conn.calls == [
        (
            "SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?",
            ("tenant-telemetry", "human_mutation"),
        )
    ]
    assert captured == [(0, "human_mutation", "tenant-telemetry")]
