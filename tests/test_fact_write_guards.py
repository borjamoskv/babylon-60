from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite
import pytest

from cortex.engine.chronos_roi import ChronosROI, ChronosReport
from cortex.engine.compound_yield import CompoundReport, CompoundYieldTracker
from cortex.engine.endocrine import ENDOCRINE
from cortex.engine.growth import NeuralGrowthEngine
from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon
from cortex.extensions.daemon.frontier import FrontierDaemon
from cortex.extensions.daemon.zero_prompting import ZeroPromptingDaemon
from cortex.memory.memory_archaeology import MemoryArchaeologist


def test_chronos_report_uses_canonical_store_callback(tmp_path: Path):
    db_path = tmp_path / "chronos.db"
    captured: dict[str, Any] = {}

    def store_fact(**kwargs: Any) -> int:
        captured.update(kwargs)
        return 42

    report = ChronosReport(
        file_count=3,
        git_commits=1,
        git_added=10,
        git_deleted=2,
        hours_saved=1.5,
        money_saved=150.0,
        roi_ratio=2.0,
        cost=75.0,
    )

    fact_id = ChronosROI().persist_report(
        report,
        str(db_path),
        project="project-a",
        tenant_id="tenant-a",
        store_fact=store_fact,
    )

    with sqlite3.connect(db_path) as conn:
        signal_tenant = conn.execute("SELECT tenant_id FROM signals").fetchone()[0]

    assert fact_id == 42
    assert captured["tenant_id"] == "tenant-a"
    assert captured["project"] == "project-a"
    assert captured["source"] == "chronos-roi"
    assert captured["confidence"] == "verified"
    assert signal_tenant == "tenant-a"


def test_compound_report_uses_canonical_store_callback(tmp_path: Path):
    db_path = tmp_path / "compound.db"
    captured: dict[str, Any] = {}

    def store_fact(**kwargs: Any) -> int:
        captured.update(kwargs)
        return 99

    report = CompoundReport(chains=[], total_linear=0, total_compound=0, multiplier=0, reuse_rate=0)
    tracker = CompoundYieldTracker(db_path=str(db_path))

    fact_id = tracker.persist_report(
        report,
        project="project-b",
        tenant_id="tenant-b",
        store_fact=store_fact,
    )

    with sqlite3.connect(db_path) as conn:
        signal_tenant = conn.execute("SELECT tenant_id FROM signals").fetchone()[0]

    assert fact_id == 99
    assert captured["tenant_id"] == "tenant-b"
    assert captured["source"] == "chronos-compound"
    assert captured["confidence"] == "verified"
    assert signal_tenant == "tenant-b"


@pytest.mark.asyncio
async def test_growth_blocks_direct_axiom_promotion_without_storer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ENDOCRINE, "get_level", lambda *_args, **_kwargs: 1.0)
    monkeypatch.setattr(ENDOCRINE, "pulse", lambda *_args, **_kwargs: None)

    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                valid_until TEXT,
                confidence TEXT,
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT
            )
            """
        )
        await conn.executemany(
            """
            INSERT INTO facts (tenant_id, project, content, fact_type, valid_until)
            VALUES (?, ?, ?, 'bridge', NULL)
            """,
            [
                ("tenant-a", "p1", "repeatable pattern",),
                ("tenant-a", "p2", "repeatable pattern",),
                ("tenant-a", "p3", "repeatable pattern",),
                ("tenant-b", "p1", "repeatable pattern",),
                ("tenant-b", "p2", "repeatable pattern",),
                ("tenant-b", "p3", "repeatable pattern",),
            ],
        )
        await conn.commit()

        promoted = await NeuralGrowthEngine()._promote_successful_bridges(
            conn,
            storer=None,
            tenant_id="tenant-a",
        )

        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE fact_type = 'axiom'")
        axiom_count = (await cursor.fetchone())[0]

    assert promoted == 0
    assert axiom_count == 0


class _ArchaeologyEngine:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _get_sync_conn(self) -> sqlite3.Connection:
        return self._conn


def test_memory_archaeology_fetches_active_facts_by_tenant():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_decision_id TEXT,
                is_tombstoned INTEGER NOT NULL,
                fact_type TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO facts
                (id, tenant_id, project, content, parent_decision_id, is_tombstoned, fact_type)
            VALUES (?, ?, ?, ?, NULL, 0, 'knowledge')
            """,
            [
                ("fact-a", "tenant-a", "shared-project", "tenant a fact"),
                ("fact-b", "tenant-b", "shared-project", "tenant b fact"),
            ],
        )

        archaeologist = MemoryArchaeologist(_ArchaeologyEngine(conn))
        facts = archaeologist._fetch_active_facts("shared-project", "tenant-a")

    finally:
        conn.close()

    assert list(facts) == ["fact-a"]
    assert facts["fact-a"]["tenant_id"] == "tenant-a"


class _SyncStoreEngine:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def store_sync(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return len(self.calls)


class _AsyncStoreEngine:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def store(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return len(self.calls)


def test_frontier_daemon_logs_evolution_through_canonical_store():
    engine = _SyncStoreEngine()

    FrontierDaemon(engine=engine)._log_evolution("ingestion", "analyzed source")

    assert len(engine.calls) == 1
    assert engine.calls[0]["tenant_id"] == "default"
    assert engine.calls[0]["fact_type"] == "decision"
    assert engine.calls[0]["source"] == "frontier-daemon"


def test_entropic_wake_logs_action_through_canonical_store():
    engine = _SyncStoreEngine()

    EntropicWakeDaemon(engine=engine)._log_action_to_cortex("target.py")

    assert len(engine.calls) == 1
    assert engine.calls[0]["tenant_id"] == "default"
    assert engine.calls[0]["fact_type"] == "decision"
    assert engine.calls[0]["source"] == "entropic-wake-daemon"


@pytest.mark.asyncio
async def test_zero_prompting_crystallizes_through_canonical_store(tmp_path: Path):
    engine = _AsyncStoreEngine()

    await ZeroPromptingDaemon(engine=engine, workspace_root=tmp_path)._crystallize(
        "reduce entropy",
        {"tool": "noop"},
        {"net_positive": True},
    )

    assert len(engine.calls) == 1
    assert engine.calls[0]["tenant_id"] == "default"
    assert engine.calls[0]["fact_type"] == "decision"
    assert engine.calls[0]["source"] == "zero-prompting-daemon"
