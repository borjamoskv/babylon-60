from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cortex.engine import CortexEngine


@pytest.mark.asyncio
async def test_session_rolls_back_open_transaction_after_cancellation(tmp_path: Path) -> None:
    engine = CortexEngine(db_path=tmp_path / "session-cancel.db", auto_embed=False)
    await engine.init_db()

    try:
        async with engine.session() as conn:
            await conn.execute("CREATE TABLE IF NOT EXISTS cancel_probe (id INTEGER PRIMARY KEY)")
            await conn.commit()

        with pytest.raises(asyncio.CancelledError):
            async with engine.session() as conn:
                await conn.execute("INSERT INTO cancel_probe (id) VALUES (1)")
                raise asyncio.CancelledError()

        assert engine.get_connection().in_transaction is False

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM cancel_probe")
            row = await cursor.fetchone()

        assert row[0] == 0
    finally:
        await engine.close()


class _FakePoolAcquire:
    def __init__(self, conn: object) -> None:
        self._conn = conn

    async def __aenter__(self) -> object:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakePool:
    def __init__(self, conn: object) -> None:
        self._conn = conn

    def acquire(self) -> _FakePoolAcquire:
        return _FakePoolAcquire(self._conn)


class _FakeConn:
    def __init__(self) -> None:
        self.in_transaction = True
        self.rollback = AsyncMock(side_effect=self._rollback)

    async def _rollback(self) -> None:
        self.in_transaction = False


@pytest.mark.asyncio
async def test_session_rolls_back_pooled_connection_after_cancellation() -> None:
    engine = CortexEngine(db_path=":memory:", auto_embed=False)
    conn = _FakeConn()
    engine._pool = _FakePool(conn)

    with pytest.raises(asyncio.CancelledError):
        async with engine.session():
            raise asyncio.CancelledError()

    conn.rollback.assert_awaited_once()
    assert conn.in_transaction is False
