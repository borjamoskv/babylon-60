from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes import telemetry as telemetry_router


class _FakeCursor:
    def __init__(self, rows: Sequence[tuple[object, ...]]) -> None:
        self._rows = list(rows)

    async def fetchone(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None

    async def fetchall(self) -> list[tuple[object, ...]]:
        return list(self._rows)


class _FakeConnection:
    def __init__(
        self,
        facts: list[dict[str, object]],
        max_id_overrides: dict[tuple[str, str], int] | None = None,
    ) -> None:
        self._facts = facts
        self._max_id_overrides = max_id_overrides or {}

    async def execute(
        self,
        sql: str,
        params: Sequence[object] | None = None,
    ) -> _FakeCursor:
        normalized_sql = " ".join(sql.split())
        query_params = tuple(params or ())

        if normalized_sql.startswith("SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?"):
            tenant_id, fact_type = query_params
            if (tenant_id, fact_type) in self._max_id_overrides:
                return _FakeCursor([(self._max_id_overrides[(tenant_id, fact_type)],)])

            matching = [
                int(fact["id"])
                for fact in self._facts
                if fact["tenant_id"] == tenant_id and fact["fact_type"] == fact_type
            ]
            return _FakeCursor([(max(matching) if matching else 0,)])

        if "WHERE fact_type = ? AND id > ? AND tenant_id = ?" in normalized_sql:
            fact_type, last_id, tenant_id = query_params
            rows = [
                (
                    fact["id"],
                    fact["content"],
                    fact["meta"],
                )
                for fact in self._facts
                if fact["fact_type"] == fact_type
                and int(fact["id"]) > int(last_id)
                and fact["tenant_id"] == tenant_id
            ]
            return _FakeCursor(rows)

        raise AssertionError(f"Unexpected SQL: {normalized_sql} params={query_params}")


class _FakeSession:
    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConnection:
        return self._conn

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeEngine:
    def __init__(
        self,
        facts: list[dict[str, object]],
        *,
        max_id_overrides: dict[tuple[str, str], int] | None = None,
    ) -> None:
        self._conn = _FakeConnection(facts, max_id_overrides=max_id_overrides)

    def session(self) -> _FakeSession:
        return _FakeSession(self._conn)


class _AuthManager:
    def __init__(self, result: AuthResult) -> None:
        self._result = result

    async def authenticate_async(self, _: str) -> AuthResult:
        return self._result


def _build_app(engine: _FakeEngine) -> FastAPI:
    app = FastAPI()
    app.include_router(telemetry_router.router)
    app.dependency_overrides[get_async_engine] = lambda: engine
    return app


@pytest.mark.parametrize("path", ["/telemetry/ast-oracle", "/telemetry/fiat-stream"])
def test_telemetry_websockets_block_unauthenticated_access(path: str) -> None:
    app = _build_app(_FakeEngine([]))

    with TestClient(app) as client:
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(path):
                pass

    status_code = getattr(exc_info.value, "status_code", None)
    if status_code is None:
        response = getattr(exc_info.value, "response", None)
        status_code = getattr(response, "status_code", None)

    if status_code is not None:
        assert status_code == 401
        return

    if exc_info.value.__class__.__name__ == "WebSocketDenialResponse":
        return

    assert isinstance(exc_info.value, WebSocketDisconnect)
    assert exc_info.value.code == 1008


@pytest.mark.parametrize(
    ("path", "fact_type", "event_name"),
    [
        ("/telemetry/ast-oracle", "human_mutation", "human_mutation"),
        ("/telemetry/fiat-stream", "fiat_transaction", "fiat_transaction"),
    ],
)
def test_telemetry_websockets_only_stream_authenticated_tenant_facts(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    fact_type: str,
    event_name: str,
) -> None:
    facts = [
        {
            "id": 11,
            "tenant_id": "tenant-alpha",
            "fact_type": fact_type,
            "content": "tenant alpha only",
            "meta": json.dumps({"tenant": "tenant-alpha"}),
        },
        {
            "id": 12,
            "tenant_id": "tenant-beta",
            "fact_type": fact_type,
            "content": "cross-tenant row",
            "meta": json.dumps({"tenant": "tenant-beta"}),
        },
    ]
    engine = _FakeEngine(
        facts,
        max_id_overrides={("tenant-alpha", fact_type): 0},
    )
    app = _build_app(engine)

    monkeypatch.setattr(
        telemetry_router,
        "get_auth_manager",
        lambda: _AuthManager(
            AuthResult(authenticated=True, tenant_id="tenant-alpha", permissions=["read"])
        ),
    )

    async def _stop_after_first_poll(_: float) -> None:
        raise WebSocketDisconnect()

    monkeypatch.setattr(telemetry_router.asyncio, "sleep", _stop_after_first_poll)

    with TestClient(app) as client:
        with client.websocket_connect(path, headers={"authorization": "Bearer test-key"}) as ws:
            payload = ws.receive_json()

    assert payload == {
        "event": event_name,
        "data": {
            "fact_id": 11,
            "content": "tenant alpha only",
            "meta": {"tenant": "tenant-alpha"},
        },
    }


@pytest.mark.asyncio
async def test_query_new_facts_redacts_sensitive_telemetry_payloads() -> None:
    facts = [
        {
            "id": 21,
            "tenant_id": "tenant-alpha",
            "fact_type": "fiat_transaction",
            "content": (
                "charged card 4111 1111 1111 1111 with "
                "Bearer ctx_supersecrettelemetrytoken"
            ),
            "meta": json.dumps(
                {
                    "tenant": "tenant-alpha",
                    "amount": "12.00",
                    "authorization": "Bearer ctx_supersecretmetatoken",
                    "operator_email": "alice@example.com",
                    "statement_path": "/Users/example/private/statement.pdf",
                    "nested": {"api_key": "ctx_nestedsecrettelemetrytoken"},
                }
            ),
        }
    ]

    _, results = await telemetry_router.query_new_facts(
        _FakeEngine(facts),
        "tenant-alpha",
        0,
        "fiat_transaction",
    )

    assert results[0]["meta"]["amount"] == "12.00"
    assert results[0]["meta"]["authorization"] == "[REDACTED]"
    assert results[0]["meta"]["nested"]["api_key"] == "[REDACTED]"

    serialized = json.dumps(results, sort_keys=True)
    assert "4111 1111 1111 1111" not in serialized
    assert "ctx_supersecrettelemetrytoken" not in serialized
    assert "ctx_supersecretmetatoken" not in serialized
    assert "ctx_nestedsecrettelemetrytoken" not in serialized
    assert "alice@example.com" not in serialized
    assert "/Users/example" not in serialized
    assert "[REDACTED_TOKEN]" in serialized
    assert "[REDACTED_PATH]" in serialized
