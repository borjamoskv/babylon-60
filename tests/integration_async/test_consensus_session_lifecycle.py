from __future__ import annotations

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
    max_connections: int = 1,
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
            VALUES (?, 'consensus', 'fact under vote', 'knowledge', '[]', '{}', 'stated')
            """,
            (tenant_id,),
        )
        await conn.commit()
        return int(cursor.lastrowid)


@pytest.mark.asyncio
async def test_consensus_methods_return_connections_to_pool(tmp_path: Path) -> None:
    engine, pool = await _build_async_engine(tmp_path / "consensus-lifecycle.db")
    manager = ConsensusManager(engine)

    try:
        fact_id = await _insert_fact(engine)

        agent_id = await manager.register_agent(name="agent-alpha")
        assert pool._pool.qsize() == 1
        assert pool._semaphore._value == 1

        legacy_score = await manager.vote(fact_id, "legacy-agent", 1)
        assert legacy_score > 0.0
        assert pool._pool.qsize() == 1
        assert pool._semaphore._value == 1

        weighted_score = await manager.vote_v2(
            fact_id,
            agent_id,
            1,
            reason="session lifecycle regression test",
        )
        assert weighted_score > 0.0
        assert pool._pool.qsize() == 1
        assert pool._semaphore._value == 1

        async with engine.session() as conn:
            async with conn.execute("SELECT COUNT(*) FROM transactions") as cursor:
                tx_count = (await cursor.fetchone())[0]
        assert tx_count >= 2
    finally:
        await pool.close()
