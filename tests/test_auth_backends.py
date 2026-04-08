from __future__ import annotations

import asyncio
import sys
import types

import pytest

from cortex.auth.backends import AlloyDBAuthBackend
from cortex.auth.schema import PG_AUTH_SCHEMA


class _FakeConn:
    def __init__(self) -> None:
        self.executed: list[str] = []

    async def execute(self, sql: str) -> None:
        self.executed.append(sql)


class _FakeAcquire:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, *args) -> None:
        return None


class _FakePool:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self._conn)


@pytest.mark.asyncio
async def test_alloydb_backend_reuses_pool_under_concurrency(monkeypatch) -> None:
    backend = AlloyDBAuthBackend("postgresql://cortex:test@localhost/cortex")
    create_pool_calls = 0
    created_pool = object()

    async def _create_pool(dsn: str):
        nonlocal create_pool_calls
        create_pool_calls += 1
        assert dsn == backend.dsn
        await asyncio.sleep(0)
        return created_pool

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(create_pool=_create_pool))

    pools = await asyncio.gather(*(backend._get_pool() for _ in range(8)))

    assert create_pool_calls == 1
    assert pools == [created_pool] * 8


@pytest.mark.asyncio
async def test_alloydb_backend_initialize_uses_explicit_postgres_schema(monkeypatch) -> None:
    backend = AlloyDBAuthBackend("postgresql://cortex:test@localhost/cortex")
    conn = _FakeConn()
    pool = _FakePool(conn)

    async def _create_pool(dsn: str):
        assert dsn == backend.dsn
        return pool

    monkeypatch.setitem(sys.modules, "asyncpg", types.SimpleNamespace(create_pool=_create_pool))

    await backend.initialize()

    assert conn.executed == [PG_AUTH_SCHEMA]
    assert "AUTOINCREMENT" not in conn.executed[0]
    assert "strftime(" not in conn.executed[0]
