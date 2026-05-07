from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
import pytest

from cortex.engine.transaction_mixin import TransactionMixin
from cortex.extensions.cuatrida.models import Dimension
from cortex.extensions.cuatrida.orchestrator import CuatridaOrchestrator
from cortex.extensions.daemon.monitors.cloud import CloudSyncMonitor
from cortex.extensions.vex.loop import VEXRunner
from cortex.extensions.vex.models import PlannedStep, TaskPlan
from cortex.utils.canonical import compute_tx_hash


TRANSACTIONS_SCHEMA = """
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    project TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""


class _LedgerEngine(TransactionMixin):
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn
        self._ledger = None

    async def get_conn(self) -> aiosqlite.Connection:
        return self._conn

    @asynccontextmanager
    async def session(self):
        yield self._conn


@pytest.mark.asyncio
async def test_vex_records_transactions_through_tenant_bound_ledger():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(TRANSACTIONS_SCHEMA)
        await conn.commit()

        engine = _LedgerEngine(conn)
        runner = VEXRunner(engine, tenant_id="tenant-vex")
        plan = TaskPlan(task_id="task-1", intent="verify chain")
        step = PlannedStep(
            step_id="step-1",
            description="run deterministic command",
            tool="noop",
        )

        await runner._record_plan_transaction(plan)
        tx_hash = await runner._record_step_transaction(
            "task-1",
            step,
            success=True,
            output="deterministic output",
            error=None,
            duration_ms=12,
        )

        cursor = await conn.execute(
            "SELECT tenant_id, project, action, detail, prev_hash, hash, timestamp "
            "FROM transactions ORDER BY id"
        )
        rows = await cursor.fetchall()

    assert [row[0] for row in rows] == ["tenant-vex", "tenant-vex"]
    assert rows[0][2] == "vex_plan"
    assert rows[1][2] == "vex_step:step-1"
    assert rows[1][4] == rows[0][5]
    assert tx_hash == rows[1][5]
    assert (
        compute_tx_hash(
            rows[1][4],
            rows[1][1],
            rows[1][2],
            rows[1][3],
            rows[1][6],
            tenant_id="tenant-vex",
        )
        == rows[1][5]
    )


@pytest.mark.asyncio
async def test_cuatrida_logs_decision_through_tenant_bound_ledger():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(TRANSACTIONS_SCHEMA)
        await conn.commit()

        engine = _LedgerEngine(conn)
        node = await CuatridaOrchestrator(engine).log_decision(
            project="project-a",
            intent="seal decision",
            dimension=Dimension.TEMPORAL_SOVEREIGNTY,
            metadata={"risk": "p0"},
            tenant_id="tenant-cuatrida",
        )

        cursor = await conn.execute(
            "SELECT id, tenant_id, project, action, detail, prev_hash, hash, timestamp "
            "FROM transactions"
        )
        row = await cursor.fetchone()

    assert node.tx_id == row[0]
    assert row[1] == "tenant-cuatrida"
    assert row[3] == "cuatrida:B"
    assert (
        compute_tx_hash(
            row[5],
            row[2],
            row[3],
            row[4],
            row[7],
            tenant_id="tenant-cuatrida",
        )
        == row[6]
    )


class _SyncEngine:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _get_sync_conn(self) -> sqlite3.Connection:
        return self._conn


class _FakeTurso:
    def __init__(self):
        self.executed_sql = ""
        self.executed_params: list[tuple[Any, ...]] = []

    async def execute(self, sql: str):
        if "SELECT MAX" in sql:
            return [{"max_id": 0}]
        return []

    async def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        self.executed_sql = sql
        self.executed_params = params


def test_cloud_sync_preserves_tenant_id_in_edge_copy():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(TRANSACTIONS_SCHEMA)
        conn.execute(
            """
            INSERT INTO transactions
                (tenant_id, project, action, detail, prev_hash, hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("tenant-edge", "project-a", "store", "{}", "GENESIS", "hash-1", "2026-01-01"),
        )
        conn.commit()

        turso = _FakeTurso()
        monitor = CloudSyncMonitor(interval_seconds=0, engine=_SyncEngine(conn))
        monitor._turso = turso

        alerts = monitor.check()

        assert len(alerts) == 1
        assert "tenant_id" in turso.executed_sql
        assert turso.executed_params[0][1] == "tenant-edge"
    finally:
        conn.close()
