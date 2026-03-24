"""Autonomous Cloud Edge Synchronization Monitor for MOSKV daemon."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from typing import Any

from cortex import config
from cortex.extensions.daemon.models import CloudSyncAlert
from cortex.storage.env import get_postgres_dsn
from cortex.storage.turso import TursoBackend

logger = logging.getLogger("moskv-daemon")

_TURSO_TRANSACTIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
"""


class CloudSyncMonitor:
    """Incrementally sync local persistence into a cloud backend.

    The monitor runs off the daemon loop, keeping the local write path fast while
    opportunistically replicating durable state to a remote backend.
    """

    def __init__(
        self,
        interval_seconds: int = 15,  # Sync every 15s by default
        engine: Any = None,
        batch_size: int = 100,
        remote_backend: Any = None,
        target_name: str | None = None,
    ):
        self.interval_seconds = interval_seconds
        self._last_run: float = 0.0
        self._engine = engine
        self._batch_size = batch_size
        self._remote = remote_backend
        self._target_name = target_name or ""
        self._schema_ready = False

        if self._remote is not None:
            self._target_name = self._target_name or "custom"
            return

        postgres_dsn = get_postgres_dsn()
        if postgres_dsn:
            from cortex.storage.postgres import PostgresBackend

            self._remote = PostgresBackend(dsn=postgres_dsn)
            self._target_name = "postgres"
        elif config.TURSO_DATABASE_URL and config.TURSO_AUTH_TOKEN:
            self._remote = TursoBackend(
                url=config.TURSO_DATABASE_URL,
                auth_token=config.TURSO_AUTH_TOKEN,
            )
            self._target_name = "turso"

    def _run_async(self, awaitable: Any) -> Any:
        """Run async backend operations from the daemon's synchronous loop."""
        return asyncio.run(awaitable)

    def _ensure_remote_schema(self) -> None:
        """Connect the remote backend and ensure the minimum sync schema exists."""
        if self._remote is None or self._schema_ready:
            return

        self._run_async(self._remote.connect())
        if self._target_name == "turso":
            self._run_async(self._remote.execute(_TURSO_TRANSACTIONS_SCHEMA))
        self._schema_ready = True

    def _get_last_synced_id(self, table: str) -> int:
        """Read the latest synced primary key for a supported remote table."""
        if self._remote is None or table not in {"transactions", "facts"}:
            return 0

        try:
            res = self._run_async(self._remote.execute(f"SELECT MAX(id) as max_id FROM {table}"))
            if res and res[0].get("max_id") is not None:
                return int(res[0]["max_id"])
        except Exception as e:  # noqa: BLE001
            logger.warning("CloudSync: Failed to get remote sync state for %s: %s", table, e)
        return 0

    @staticmethod
    def _coerce_meta_json(raw_meta: Any) -> str:
        """Serialize SQLite metadata into valid JSON for PostgreSQL JSONB."""
        if raw_meta in (None, ""):
            return "{}"
        if isinstance(raw_meta, (dict, list, int, float, bool)):
            return json.dumps(raw_meta)
        if isinstance(raw_meta, str):
            try:
                decoded = json.loads(raw_meta)
            except json.JSONDecodeError:
                return json.dumps(raw_meta)
            return json.dumps(decoded)
        return json.dumps(str(raw_meta))

    def _sync_transactions(self, conn: sqlite3.Connection) -> tuple[int, int]:
        """Sync append-only ledger transactions to the remote backend."""
        if self._remote is None:
            return 0, 0

        last_id = self._get_last_synced_id("transactions")
        cursor = conn.execute(
            "SELECT id, tenant_id, project, action, detail, prev_hash, hash, timestamp "
            "FROM transactions WHERE id > ? ORDER BY id ASC LIMIT ?",
            (last_id, self._batch_size),
        )
        rows = cursor.fetchall()
        if not rows:
            return 0, last_id

        if self._target_name == "postgres":
            sql = (
                "INSERT INTO transactions "
                "(id, tenant_id, project, action, detail, prev_hash, hash, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING"
            )
            params_list = [
                (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]) for row in rows
            ]
        else:
            sql = (
                "INSERT INTO transactions "
                "(id, project, action, detail, prev_hash, hash, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING"
            )
            params_list = [
                (row[0], row[2], row[3], row[4], row[5], row[6], row[7]) for row in rows
            ]

        self._run_async(self._remote.executemany(sql, params_list))
        return len(rows), int(rows[-1][0])

    def _sync_facts(self, conn: sqlite3.Connection) -> tuple[int, int]:
        """Sync facts to PostgreSQL/AlloyDB for cloud L3 durability."""
        if self._remote is None or self._target_name != "postgres":
            return 0, 0

        last_id = self._get_last_synced_id("facts")
        cursor = conn.execute(
            "SELECT "
            "id, tenant_id, project, content, fact_type, tags, confidence, "
            "COALESCE(valid_from, created_at, updated_at, datetime('now')), "
            "valid_until, source, metadata, COALESCE(consensus_score, 0.0), hash, "
            "is_quarantined, quarantined_at, quarantine_reason, "
            "COALESCE(created_at, valid_from, updated_at, datetime('now')), "
            "COALESCE(updated_at, created_at, valid_from, datetime('now')), "
            "tx_id, is_tombstoned, tombstoned_at "
            "FROM facts WHERE id > ? ORDER BY id ASC LIMIT ?",
            (last_id, self._batch_size),
        )
        rows = cursor.fetchall()
        if not rows:
            return 0, last_id

        sql = (
            "INSERT INTO facts "
            "(id, tenant_id, project, content, fact_type, tags, confidence, "
            "valid_from, valid_until, source, meta, consensus_score, hash, "
            "is_quarantined, quarantined_at, quarantine_reason, created_at, updated_at, "
            "tx_id, is_tombstoned, tombstoned_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (id) DO NOTHING"
        )
        params_list = [
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5] or "[]",
                row[6] or "stated",
                row[7],
                row[8],
                row[9],
                self._coerce_meta_json(row[10]),
                float(row[11] or 0.0),
                row[12],
                bool(row[13]),
                row[14],
                row[15],
                row[16],
                row[17],
                row[18],
                bool(row[19]),
                row[20],
            )
            for row in rows
        ]

        self._run_async(self._remote.executemany(sql, params_list))
        return len(rows), int(rows[-1][0])

    def check(self) -> list[CloudSyncAlert]:
        """Run Edge Sync if interval has elapsed."""
        if not self._engine or self._remote is None:
            return []

        now = time.monotonic()
        if now - self._last_run < self.interval_seconds:
            return []

        alerts: list[CloudSyncAlert] = []
        try:
            self._ensure_remote_schema()
            conn = self._engine._get_sync_conn()
            synced_tx, last_tx_id = self._sync_transactions(conn)
            synced_facts, last_fact_id = self._sync_facts(conn)
            synced_total = synced_tx + synced_facts

            if synced_total:
                alerts.append(
                    CloudSyncAlert(
                        synced_count=synced_total,
                        last_id=max(last_tx_id, last_fact_id),
                        message=(
                            f"Synced {synced_tx} transactions and {synced_facts} facts "
                            f"to {self._target_name} cloud."
                        ),
                        latency_ms=(time.monotonic() - now) * 1000,
                        target=self._target_name,
                        synced_transactions=synced_tx,
                        synced_facts=synced_facts,
                    )
                )

            self._last_run = now

        except (ValueError, OSError, RuntimeError, ImportError, sqlite3.Error) as e:
            logger.error("Autonomous Cloud Sync failed: %s", e)

        return alerts
