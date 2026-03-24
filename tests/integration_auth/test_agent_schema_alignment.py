from __future__ import annotations

import pytest

from cortex.consensus.manager import ConsensusManager


@pytest.mark.asyncio
async def test_consensus_manager_register_agent_matches_agents_schema(async_engine) -> None:
    manager = ConsensusManager(async_engine)

    agent_id = await manager.register_agent(
        name="agent-alpha",
        agent_type="ai",
        public_key="",
        tenant_id="tenant_a",
    )

    async with async_engine.session() as conn:
        async with conn.execute(
            """
            SELECT public_key, name, agent_type, tenant_id, base_reputation,
                   alignment_hits, alignment_misses, is_active
            FROM agents
            WHERE id = ?
            """,
            (agent_id,),
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row[0] == ""
    assert row[1] == "agent-alpha"
    assert row[2] == "ai"
    assert row[3] == "tenant_a"
    assert row[4] == 0.5
    assert row[5] == 0
    assert row[6] == 0
    assert row[7] == 1


@pytest.mark.asyncio
async def test_agent_lookup_is_tenant_scoped(async_engine) -> None:
    agent_id = await async_engine.register_agent(
        name="agent-beta",
        agent_type="ai",
        public_key="",
        tenant_id="tenant_a",
        moltbook_sync=False,
    )

    assert await async_engine.get_agent(agent_id, tenant_id="tenant_a") is not None
    assert await async_engine.get_agent(agent_id, tenant_id="tenant_b") is None
