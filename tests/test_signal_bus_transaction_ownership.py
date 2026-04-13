import aiosqlite
import pytest

from cortex.extensions.signals.bus import AsyncSignalBus


@pytest.mark.asyncio
async def test_async_signal_bus_ensure_table_does_not_commit_external_transaction(tmp_path):
    db_path = tmp_path / "signals_tx_ownership.db"

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY)")
        await conn.commit()

        await conn.execute("BEGIN IMMEDIATE")
        await conn.execute("INSERT INTO probe (id) VALUES (1)")

        bus = AsyncSignalBus(conn)
        await bus.ensure_table()
        await conn.rollback()

    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT COUNT(*) FROM probe") as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row[0] == 0
