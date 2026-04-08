from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from cortex.engine.mutation_engine import FactMutationEngine


async def _setup_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            confidence TEXT DEFAULT 'C5',
            consensus_score REAL DEFAULT 1.0,
            metadata TEXT DEFAULT '{}',
            valid_until TEXT,
            is_tombstoned INTEGER DEFAULT 0,
            is_quarantined INTEGER DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            tombstoned_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE entity_events (
            id TEXT PRIMARY KEY,
            entity_id INTEGER NOT NULL,
            tenant_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            signature TEXT NOT NULL,
            signer TEXT,
            schema_version TEXT NOT NULL
        );
        """
    )
    await conn.commit()


@pytest.mark.asyncio
async def test_tombstone_uses_fact_tenant_for_taint(monkeypatch):
    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, confidence, metadata) VALUES (?, ?, ?, ?)",
        (1, "tenant-a", "C5", "{}"),
    )
    await conn.commit()

    captured: dict[str, str] = {}

    async def fake_propagate(self, fact_id: int, tenant_id: str = "default", floor_to_c1: bool = True):
        captured["tenant_id"] = tenant_id

        class _Report:
            affected_count = 0

        return _Report()

    monkeypatch.setattr("cortex.engine.causality.AsyncCausalGraph.propagate_taint", fake_propagate)

    engine = FactMutationEngine()
    await engine.apply(
        conn,
        fact_id=1,
        tenant_id="tenant-a",
        event_type="tombstone",
        payload={"reason": "retire"},
    )

    assert captured["tenant_id"] == "tenant-a"
    await conn.close()


@pytest.mark.asyncio
async def test_replay_state_respects_as_of_filter():
    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)

    engine = FactMutationEngine()
    base = datetime.now(timezone.utc)
    early = base.isoformat()
    late = (base + timedelta(minutes=5)).isoformat()

    await conn.execute(
        "INSERT INTO entity_events (id, entity_id, tenant_id, event_type, payload, timestamp, prev_hash, signature, signer, schema_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("evt-1", 1, "tenant-a", "score_update", '{"a": 1}', early, "GENESIS", "sig-1", "", "1"),
    )
    await conn.execute(
        "INSERT INTO entity_events (id, entity_id, tenant_id, event_type, payload, timestamp, prev_hash, signature, signer, schema_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("evt-2", 1, "tenant-a", "score_update", '{"b": 2}', late, "sig-1", "sig-2", "", "1"),
    )
    await conn.commit()

    state = await engine.replay_state(conn, entity_id=1, as_of=early)

    assert state["_last_event_type"] == "score_update"
    assert state["a"] == 1
    assert "b" not in state
    await conn.close()


@pytest.mark.asyncio
async def test_score_update_updates_consensus_score_when_metadata_encrypted():
    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, confidence, consensus_score, metadata) VALUES (?, ?, ?, ?, ?)",
        (1, "tenant-a", "C5", 1.0, "v6_aesgcm:opaque"),
    )
    await conn.commit()

    engine = FactMutationEngine()
    await engine.apply(
        conn,
        fact_id=1,
        tenant_id="tenant-a",
        event_type="score_update",
        payload={"consensus_score": 0.4, "confidence": "disputed"},
    )

    async with conn.execute(
        "SELECT confidence, consensus_score, metadata FROM facts WHERE id = ?",
        (1,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == "disputed"
    assert row[1] == pytest.approx(0.4)
    assert row[2] == "v6_aesgcm:opaque"
    await conn.close()


@pytest.mark.asyncio
async def test_decalcify_updates_consensus_score_column_when_metadata_encrypted():
    conn = await aiosqlite.connect(":memory:")
    await _setup_db(conn)
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, confidence, consensus_score, metadata) VALUES (?, ?, ?, ?, ?)",
        (1, "tenant-a", "verified", 2.0, "v6_aesgcm:opaque"),
    )
    await conn.commit()

    engine = FactMutationEngine()
    await engine.apply(
        conn,
        fact_id=1,
        tenant_id="tenant-a",
        event_type="decalcify",
        payload={"decay_factor": 0.5},
    )

    async with conn.execute(
        "SELECT confidence, consensus_score, metadata FROM facts WHERE id = ?",
        (1,),
    ) as cursor:
        row = await cursor.fetchone()

    assert row[0] == "tentative"
    assert row[1] == pytest.approx(1.0)
    assert row[2] == "v6_aesgcm:opaque"
    await conn.close()
