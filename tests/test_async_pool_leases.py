from __future__ import annotations

import asyncio

import pytest

from cortex.database.pool import CortexConnectionPool


@pytest.mark.asyncio
async def test_pool_get_conn_releases_slot_on_close(tmp_path):
    db_path = tmp_path / "lease-test.db"
    pool = CortexConnectionPool(
        str(db_path),
        min_connections=0,
        max_connections=1,
        read_only=False,
    )

    first = await pool.get_conn()
    try:
        cursor = await first.execute("SELECT 1")
        row = await cursor.fetchone()
        assert row[0] == 1

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(pool.get_conn(), timeout=0.05)
    finally:
        await first.close()

    second = await asyncio.wait_for(pool.get_conn(), timeout=0.2)
    try:
        cursor = await second.execute("SELECT 1")
        row = await cursor.fetchone()
        assert row[0] == 1
    finally:
        await second.close()
        await pool.close()


@pytest.mark.asyncio
async def test_pool_get_conn_supports_async_with(tmp_path):
    db_path = tmp_path / "lease-context.db"
    pool = CortexConnectionPool(
        str(db_path),
        min_connections=0,
        max_connections=1,
        read_only=False,
    )

    async with await pool.get_conn() as conn:
        cursor = await conn.execute("SELECT 1")
        row = await cursor.fetchone()
        assert row[0] == 1

    lease = await asyncio.wait_for(pool.get_conn(), timeout=0.2)
    await lease.close()
    await pool.close()
