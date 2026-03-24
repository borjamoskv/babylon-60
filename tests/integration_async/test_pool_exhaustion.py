from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from cortex.consensus.manager import ConsensusManager
from cortex.database.pool import CortexConnectionPool
from cortex.database.schema import get_init_meta
from cortex.engine_async import AsyncCortexEngine
from cortex.migrations.core import run_migrations_async


async def _build_async_engine(
    db_path: Path,
    *,
    min_connections: int = 1,
    max_connections: int = 2,
) -> tuple[AsyncCortexEngine, CortexConnectionPool]:
    pool = CortexConnectionPool(
        str(db_path),
        min_connections=min_connections,
        max_connections=max_connections,
        read_only=False,
    )
    await pool.initialize()

    async with pool.acquire() as conn:
        await run_migrations_async(conn)
        for key, value in get_init_meta():
            await conn.execute(
                "INSERT OR IGNORE INTO cortex_meta (key, value) VALUES (?, ?)",
                (key, value),
            )
        await conn.commit()

    return AsyncCortexEngine(pool=pool, db_path=str(db_path)), pool


async def _insert_fact(engine: AsyncCortexEngine, *, tenant_id: str = "default") -> int:
    async with engine.session() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO facts (tenant_id, project, content, fact_type, tags, metadata, confidence)
            VALUES (?, 'consensus', 'concurrent fact', 'knowledge', '[]', '{}', 'stated')
            """,
            (tenant_id,),
        )
        await conn.commit()
        return int(cursor.lastrowid)


@pytest.mark.asyncio
async def test_consensus_manager_does_not_exhaust_pool_under_load(tmp_path: Path) -> None:
    engine, pool = await _build_async_engine(
        tmp_path / "pool-exhaustion.db",
        min_connections=1,
        max_connections=2,
    )
    manager = ConsensusManager(engine)

    try:
        fact_id = await _insert_fact(engine)

        async def register_and_vote(idx: int) -> float:
            agent_id = await manager.register_agent(name=f"agent-{idx}")
            return await manager.vote_v2(
                fact_id,
                agent_id,
                1 if idx % 2 == 0 else -1,
                reason=f"concurrent-{idx}",
            )

        scores = await asyncio.wait_for(
            asyncio.gather(*(register_and_vote(i) for i in range(8))),
            timeout=10,
        )

        assert len(scores) == 8
        assert pool._active_count <= pool.max_connections
        assert pool._pool.qsize() == pool._active_count
        assert pool._semaphore._value == pool.max_connections

        async with engine.session() as conn:
            async with conn.execute("SELECT COUNT(*) FROM consensus_votes_v2") as cursor:
                vote_count = (await cursor.fetchone())[0]
        assert vote_count == 8
    finally:
        await pool.close()
