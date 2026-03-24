from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from cortex.extensions.daemon.monitors.cloud import CloudSyncMonitor


class FakeRemoteBackend:
    def __init__(self, max_ids: dict[str, int] | None = None):
        self.max_ids = max_ids or {}
        self.connected = 0
        self.executed: list[str] = []
        self.batches: list[tuple[str, list[tuple[Any, ...]]]] = []

    async def connect(self) -> None:
        self.connected += 1

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        del params
        self.executed.append(sql)
        if "MAX(id)" in sql:
            table = "facts" if "FROM facts" in sql else "transactions"
            return [{"max_id": self.max_ids.get(table)}]
        return []

    async def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        self.batches.append((sql, list(params_list)))


class FakeEngine:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _get_sync_conn(self) -> sqlite3.Connection:
        return self._conn


def _build_local_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "cloud-sync.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            tags TEXT NOT NULL DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            hash TEXT,
            valid_from TEXT,
            valid_until TEXT,
            source TEXT,
            confidence TEXT DEFAULT 'stated',
            consensus_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            tx_id INTEGER,
            is_tombstoned INTEGER NOT NULL DEFAULT 0,
            is_quarantined INTEGER NOT NULL DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            tombstoned_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO transactions (id, tenant_id, project, action, detail, prev_hash, hash, timestamp)
        VALUES (1, 'tenant-a', 'demo', 'store', '{"ok":true}', 'GENESIS', 'hash-1', '2026-03-24T10:00:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO facts (
            id, tenant_id, project, content, fact_type, tags, metadata, hash,
            valid_from, source, confidence, consensus_score, created_at, updated_at, tx_id
        )
        VALUES (
            1, 'tenant-a', 'demo', 'ciphertext', 'knowledge', '["roadmap"]', 'opaque-ciphertext',
            'fact-hash', '2026-03-24T10:00:00Z', 'unit-test', 'stated', 0.8,
            '2026-03-24T10:00:00Z', '2026-03-24T10:00:00Z', 1
        )
        """
    )
    conn.commit()
    return conn


def test_cloud_sync_monitor_syncs_transactions_and_facts_to_postgres(tmp_path: Path) -> None:
    conn = _build_local_db(tmp_path)
    remote = FakeRemoteBackend()
    monitor = CloudSyncMonitor(
        interval_seconds=0,
        engine=FakeEngine(conn),
        remote_backend=remote,
        target_name="postgres",
    )

    alerts = monitor.check()

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.target == "postgres"
    assert alert.synced_transactions == 1
    assert alert.synced_facts == 1
    assert alert.synced_count == 2
    assert alert.last_id == 1
    assert remote.connected == 1
    assert len(remote.batches) == 2
    assert "INSERT INTO transactions" in remote.batches[0][0]
    assert "INSERT INTO facts" in remote.batches[1][0]

    fact_row = remote.batches[1][1][0]
    assert fact_row[0] == 1
    assert fact_row[1] == "tenant-a"
    assert fact_row[10] == '"opaque-ciphertext"'
    assert fact_row[13] is False
    assert fact_row[19] is False


def test_cloud_sync_monitor_resumes_from_remote_max_ids(tmp_path: Path) -> None:
    conn = _build_local_db(tmp_path)
    remote = FakeRemoteBackend(max_ids={"transactions": 1, "facts": 1})
    monitor = CloudSyncMonitor(
        interval_seconds=0,
        engine=FakeEngine(conn),
        remote_backend=remote,
        target_name="postgres",
    )

    alerts = monitor.check()

    assert alerts == []
    assert remote.connected == 1
    assert remote.batches == []


def test_cloud_sync_monitor_keeps_turso_transaction_sync_compatible(tmp_path: Path) -> None:
    conn = _build_local_db(tmp_path)
    remote = FakeRemoteBackend()
    monitor = CloudSyncMonitor(
        interval_seconds=0,
        engine=FakeEngine(conn),
        remote_backend=remote,
        target_name="turso",
    )

    alerts = monitor.check()

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.target == "turso"
    assert alert.synced_transactions == 1
    assert alert.synced_facts == 0
    assert len(remote.batches) == 1
    sql, params = remote.batches[0]
    assert "INSERT INTO transactions" in sql
    assert len(params[0]) == 7
