from __future__ import annotations

import aiosqlite
import pytest

from cortex.consensus.manager import ConsensusManager


class _StubEngine:
    def __init__(self, conn):
        self._conn = conn

    async def get_conn(self):
        return self._conn

    async def _log_transaction(self, conn, project, action, detail):
        return 1


@pytest.mark.asyncio
async def test_vote_v2_accepts_agent_from_fact_tenant(monkeypatch) -> None:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, tenant_id TEXT)")
    await conn.execute(
        "CREATE TABLE agents (id TEXT PRIMARY KEY, tenant_id TEXT, reputation_score REAL, is_active INTEGER)"
    )
    await conn.execute(
        "CREATE TABLE consensus_votes_v2 (fact_id INTEGER, agent_id TEXT, vote INTEGER, vote_weight REAL, agent_rep_at_vote REAL, vote_reason TEXT)"
    )
    await conn.execute("INSERT INTO facts (id, tenant_id) VALUES (1, 'tenant-a')")
    await conn.execute(
        "INSERT INTO agents (id, tenant_id, reputation_score, is_active) VALUES ('agent-a', 'tenant-a', 0.8, 1)"
    )
    await conn.commit()

    manager = ConsensusManager(_StubEngine(conn))

    async def _fake_recalc(fact_id, conn):
        return 0.9

    monkeypatch.setattr(manager, "_recalculate_consensus_v2", _fake_recalc)

    score = await manager.vote_v2(1, "agent-a", 1)

    assert score == 0.9
    cursor = await conn.execute("SELECT agent_id FROM consensus_votes_v2 WHERE fact_id = 1")
    row = await cursor.fetchone()
    assert row[0] == "agent-a"
    await conn.close()


@pytest.mark.asyncio
async def test_vote_v2_rejects_agent_from_other_tenant(monkeypatch) -> None:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY, tenant_id TEXT)")
    await conn.execute(
        "CREATE TABLE agents (id TEXT PRIMARY KEY, tenant_id TEXT, reputation_score REAL, is_active INTEGER)"
    )
    await conn.execute(
        "CREATE TABLE consensus_votes_v2 (fact_id INTEGER, agent_id TEXT, vote INTEGER, vote_weight REAL, agent_rep_at_vote REAL, vote_reason TEXT)"
    )
    await conn.execute("INSERT INTO facts (id, tenant_id) VALUES (1, 'tenant-a')")
    await conn.execute(
        "INSERT INTO agents (id, tenant_id, reputation_score, is_active) VALUES ('agent-b', 'tenant-b', 0.8, 1)"
    )
    await conn.commit()

    manager = ConsensusManager(_StubEngine(conn))

    async def _fake_recalc(fact_id, conn):
        return 0.9

    monkeypatch.setattr(manager, "_recalculate_consensus_v2", _fake_recalc)

    with pytest.raises(ValueError) as excinfo:
        await manager.vote_v2(1, "agent-b", 1)

    assert "not found" in str(excinfo.value)
    cursor = await conn.execute("SELECT COUNT(*) FROM consensus_votes_v2")
    row = await cursor.fetchone()
    assert row[0] == 0
    await conn.close()
