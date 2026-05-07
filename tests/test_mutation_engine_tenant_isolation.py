from __future__ import annotations

import aiosqlite
import pytest

from cortex.database.schema_extensions import CREATE_ENTITY_EVENTS, CREATE_ENTITY_EVENTS_INDEXES
from cortex.engine.mutation_engine import FactMutationEngine


async def _setup_conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    await conn.executescript(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            confidence TEXT,
            metadata TEXT DEFAULT '{}',
            valid_until TEXT,
            updated_at TEXT,
            is_tombstoned INTEGER DEFAULT 0,
            is_quarantined INTEGER DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            tombstoned_at TEXT
        );
        """
    )
    await conn.executescript(CREATE_ENTITY_EVENTS)
    await conn.executescript(CREATE_ENTITY_EVENTS_INDEXES)
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, confidence, metadata) VALUES (?, ?, ?, ?)",
        (1, "tenant-alpha", "C3", "{}"),
    )
    await conn.commit()
    return conn


@pytest.mark.asyncio
async def test_apply_rejects_foreign_tenant_fact_id() -> None:
    conn = await _setup_conn()
    try:
        engine = FactMutationEngine()

        with pytest.raises(ValueError, match="tenant-beta"):
            await engine.apply(
                conn,
                fact_id=1,
                tenant_id="tenant-beta",
                event_type="score_update",
                payload={"confidence": "verified", "consensus_score": 2.0},
            )

        cursor = await conn.execute("SELECT COUNT(*) FROM entity_events")
        assert (await cursor.fetchone())[0] == 0
        cursor = await conn.execute("SELECT confidence FROM facts WHERE id = 1")
        assert (await cursor.fetchone())[0] == "C3"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_apply_projects_only_with_matching_tenant() -> None:
    conn = await _setup_conn()
    try:
        engine = FactMutationEngine()

        await engine.apply(
            conn,
            fact_id=1,
            tenant_id="tenant-alpha",
            event_type="score_update",
            payload={"confidence": "verified", "consensus_score": 2.0},
        )

        cursor = await conn.execute("SELECT confidence FROM facts WHERE id = 1")
        assert (await cursor.fetchone())[0] == "verified"
        cursor = await conn.execute("SELECT tenant_id FROM entity_events WHERE entity_id = 1")
        assert (await cursor.fetchone())[0] == "tenant-alpha"
    finally:
        await conn.close()
