from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone

import aiosqlite
import pytest

from cortex.engine.fact_store_core import insert_fact_record
from cortex.graph.backends.sqlite import SQLiteBackend
from cortex.graph.engine import process_fact_graph
from cortex.memory.temporal import build_temporal_filter_params, time_travel_filter


async def _setup_facts_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT DEFAULT 'default',
            project TEXT,
            content TEXT,
            fact_type TEXT,
            tags TEXT,
            confidence TEXT DEFAULT 'stated',
            confidence_rank INTEGER DEFAULT 3,
            valid_from TEXT,
            valid_until TEXT,
            source TEXT,
            metadata TEXT,
            hash TEXT,
            signature TEXT,
            signer_pubkey TEXT,
            is_quarantined INTEGER DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            is_tombstoned INTEGER DEFAULT 0,
            parent_decision_id INTEGER,
            parent_id INTEGER,
            relation_type TEXT,
            quadrant TEXT,
            storage_tier TEXT,
            exergy_score REAL,
            category TEXT,
            yield_score REAL,
            semantic_status TEXT,
            created_at TEXT,
            updated_at TEXT,
            consensus_score REAL DEFAULT 1.0,
            tx_id INTEGER,
            expires_at TEXT,
            last_accessed_at TEXT,
            tombstoned_at TEXT,
            cognitive_layer TEXT,
            haiku TEXT,
            falsification_test TEXT
        );
    """)
    await conn.commit()


async def _setup_graph_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            entity_type TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            first_seen TEXT,
            last_seen TEXT,
            mention_count INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER,
            target_entity_id INTEGER,
            relation_type TEXT,
            weight REAL DEFAULT 1.0,
            first_seen TEXT,
            source_fact_id INTEGER,
            tenant_id TEXT DEFAULT 'default'
        );
    """)
    await conn.commit()


def _setup_graph_schema_sync(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            entity_type TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            first_seen TEXT,
            last_seen TEXT,
            mention_count INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER,
            target_entity_id INTEGER,
            relation_type TEXT,
            weight REAL DEFAULT 1.0,
            first_seen TEXT,
            source_fact_id INTEGER,
            tenant_id TEXT DEFAULT 'default'
        );
        CREATE TABLE IF NOT EXISTS ghosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT,
            context TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            detected_at TEXT,
            resolved_at TEXT,
            target_id INTEGER,
            confidence REAL,
            status TEXT DEFAULT 'open'
        );
    """)
    conn.commit()


def _install_crypto_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cortex.engine.fact_store_core.compute_fact_hash",
        lambda _: "deadbeef",
    )

    class _FakeEnc:
        def encrypt_str(self, s: str, **kw: object) -> str:
            return s

        def encrypt_json(self, d: object, **kw: object) -> str:
            return json.dumps(d)

    class _FakeSigner:
        can_sign = False


def test_build_temporal_filter_params_prefers_columns_before_metadata() -> None:
    clause, params = build_temporal_filter_params("2026-04-07T00:00:00+00:00", table_alias="f")

    assert "coalesce(f.valid_from" in clause
    assert "f.valid_until" in clause
    assert "f.tombstoned_at" in clause
    assert "CASE WHEN f.metadata LIKE 'v6_aesgcm:%'" in clause
    assert params == ["2026-04-07T00:00:00+00:00"] * 3


def test_time_travel_filter_prefers_columns_before_metadata() -> None:
    clause, params = time_travel_filter(7, table_alias="f")

    assert "coalesce(f.tx_id" in clause
    assert "f.valid_until" in clause
    assert "f.tombstoned_at" in clause
    assert "CASE WHEN f.metadata LIKE 'v6_aesgcm:%'" in clause
    assert params == [7, 7, 7]


@pytest.mark.asyncio
async def test_insert_fact_record_normalizes_datetime_timestamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_crypto_stubs(monkeypatch)
    conn = await aiosqlite.connect(":memory:")
    await _setup_facts_schema(conn)

    ts = datetime(2026, 4, 7, 12, 30, 45, tzinfo=timezone.utc)
    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="proj",
        content="fact content",
        fact_type="knowledge",
        tags=[],
        confidence="stated",
        ts=ts,
        source="test",
        meta={},
        tx_id=None,
    )

    async with conn.execute(
        "SELECT valid_from, created_at, updated_at FROM facts WHERE id = ?",
        (fact_id,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row == (ts.isoformat(), ts.isoformat(), ts.isoformat())
    await conn.close()


@pytest.mark.asyncio
async def test_process_fact_graph_normalizes_date_timestamp() -> None:
    conn = await aiosqlite.connect(":memory:")
    await _setup_graph_schema(conn)

    entities, relationships = await process_fact_graph(
        conn,
        fact_id=1,
        content="cortex-persist uses FastAPI",
        project="proj",
        timestamp=date(2026, 4, 7),
        tenant_id="tenant-alpha",
    )

    expected_ts = "2026-04-07T00:00:00+00:00"
    assert entities >= 2
    assert relationships == 1

    async with conn.execute(
        "SELECT first_seen, last_seen FROM entities WHERE tenant_id = ? ORDER BY id ASC LIMIT 1",
        ("tenant-alpha",),
    ) as cursor:
        entity_row = await cursor.fetchone()

    async with conn.execute(
        "SELECT first_seen FROM entity_relations WHERE tenant_id = ? ORDER BY id ASC LIMIT 1",
        ("tenant-alpha",),
    ) as cursor:
        relation_row = await cursor.fetchone()

    assert entity_row == (expected_ts, expected_ts)
    assert relation_row == (expected_ts,)
    await conn.close()


def test_sqlite_graph_backend_sync_normalizes_datetime_timestamp() -> None:
    conn = sqlite3.connect(":memory:")
    _setup_graph_schema_sync(conn)
    backend = SQLiteBackend(conn)
    ts = datetime(2026, 4, 7, 10, 11, 12)

    backend.upsert_entity_sync("FastAPI", "tool", "proj", ts, tenant_id="tenant-alpha")

    row = conn.execute(
        "SELECT first_seen, last_seen FROM entities WHERE tenant_id = ?",
        ("tenant-alpha",),
    ).fetchone()
    assert row == ("2026-04-07T10:11:12+00:00", "2026-04-07T10:11:12+00:00")


@pytest.mark.asyncio
async def test_sqlite_graph_backend_async_normalizes_date_for_ghosts() -> None:
    conn = await aiosqlite.connect(":memory:")
    await _setup_graph_schema(conn)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ghosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT,
            context TEXT,
            project TEXT,
            tenant_id TEXT DEFAULT 'default',
            detected_at TEXT,
            resolved_at TEXT,
            target_id INTEGER,
            confidence REAL,
            status TEXT DEFAULT 'open'
        )
    """)
    await conn.commit()
    backend = SQLiteBackend(conn)

    await backend.upsert_ghost(
        reference="ghost-ref",
        context="ghost ctx",
        project="proj",
        timestamp=date(2026, 4, 7),
        tenant_id="tenant-alpha",
    )

    async with conn.execute(
        "SELECT detected_at FROM ghosts WHERE tenant_id = ?",
        ("tenant-alpha",),
    ) as cursor:
        row = await cursor.fetchone()

    assert row == ("2026-04-07T00:00:00+00:00",)
    await conn.close()
