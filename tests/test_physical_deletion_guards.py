from __future__ import annotations

import asyncio
import sqlite3

import aiosqlite
import pytest

from cortex.compaction.gc import GarbageCollector
from cortex.engine.decalcifier import SovereignDecalcifier
from cortex.engine.endocrine import ENDOCRINE
from cortex.extensions.daemon.monitors.tombstone import TombstoneMonitor


class _AsyncSession:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def __aenter__(self) -> aiosqlite.Connection:
        return self._conn

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class _Engine:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    def session(self) -> _AsyncSession:
        return _AsyncSession(self._conn)


@pytest.mark.asyncio
async def test_decalcifier_blocks_telemetry_ledger_deletion(monkeypatch: pytest.MonkeyPatch):
    async def fake_to_thread(func: object, *args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(ENDOCRINE, "pulse", lambda *args, **kwargs: None)

    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            """
            CREATE TABLE transactions (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            "INSERT INTO transactions (id, action, timestamp) VALUES (?, ?, ?)",
            ("tx-old-telemetry", "telemetry", "2000-01-01T00:00:00Z"),
        )
        await conn.commit()

        result = await SovereignDecalcifier().decalcify_cycle(conn)

        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        remaining = (await cursor.fetchone())[0]

    assert result["status"] == "success"
    assert result["metrics"]["purged_orphans"] == 0
    assert result["metrics"]["ledger_deletions_blocked"] == 1
    assert remaining == 1


@pytest.mark.asyncio
async def test_garbage_collector_reports_tombstones_without_physical_deletion():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                is_tombstoned INTEGER NOT NULL
            )
            """
        )
        await conn.executemany(
            "INSERT INTO facts (id, tenant_id, is_tombstoned) VALUES (?, ?, ?)",
            [
                ("fact-a", "tenant-a", 1),
                ("fact-b", "tenant-b", 1),
            ],
        )
        await conn.commit()

        result = await GarbageCollector(_Engine(conn)).run_gc(batch_size=10, force=True)

        cursor = await conn.execute("SELECT COUNT(*) FROM facts")
        remaining = (await cursor.fetchone())[0]

    assert result["status"] == "blocked"
    assert result["reason"] == "canonical_purge_required"
    assert result["blocked_facts"] == 2
    assert result["deleted_facts"] == 0
    assert result["deleted_embeddings"] == 0
    assert remaining == 2


def test_tombstone_monitor_blocks_physical_sweep(tmp_path):
    db_path = tmp_path / "cortex.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                is_tombstoned INTEGER NOT NULL
            )
            """
        )
        conn.execute("INSERT INTO facts (id, is_tombstoned) VALUES (?, ?)", ("fact-a", 1))

    monitor = TombstoneMonitor(db_path, interval_seconds=0, start_hour=0, end_hour=24)

    alerts = monitor.check()

    with sqlite3.connect(db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

    assert len(alerts) == 1
    assert alerts[0].deleted_facts == 0
    assert alerts[0].freed_mb == 0.0
    assert "canonical tenant-scoped purge" in alerts[0].message
    assert remaining == 1
