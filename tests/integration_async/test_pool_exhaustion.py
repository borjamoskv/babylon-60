import asyncio
import logging
import os
import sqlite3
import traceback
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine

# Needed for mutation engine / flake generator
os.environ["MOSKV_WORKER_ID"] = "1"

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
async def async_engine(tmp_path: Path) -> AsyncGenerator[AsyncCortexEngine, None]:
    db_path = str(tmp_path / "test_exhaustion.db")

    # 2. Setup standard tables (minimal for performance)
    from cortex.database.schema import (
        CREATE_AGENTS,
        CREATE_ENTITY_EVENTS,
        CREATE_FACTS,
        CREATE_MERKLE_ROOTS,
        CREATE_TRANSACTIONS,
        CREATE_VOTES_V2,
    )
    from cortex.database.schema import (
        CREATE_VOTES as CREATE_VOTES_V1,
    )

    conn = sqlite3.connect(db_path)
    # Define legacy vote_ledger here if not in schema re-exports
    # or just use the one we had if it's test-specific.
    conn.executescript(f"""
        PRAGMA journal_mode=WAL;
        {CREATE_AGENTS}
        {CREATE_ENTITY_EVENTS}
        {CREATE_FACTS}
        {CREATE_TRANSACTIONS}
        {CREATE_VOTES_V1}
        {CREATE_VOTES_V2}
        {CREATE_MERKLE_ROOTS}
        -- Test specific legacy ledger if needed
        CREATE TABLE IF NOT EXISTS vote_ledger (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id         INTEGER NOT NULL,
            agent_id        TEXT NOT NULL,
            vote            INTEGER NOT NULL,
            vote_weight     REAL NOT NULL,
            prev_hash       TEXT NOT NULL,
            hash            TEXT NOT NULL,
            timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
            signature       TEXT,
            UNIQUE(hash)
        );
    """)
    conn.commit()
    conn.close()

    # Small pool to force contention
    pool = CortexConnectionPool(
        db_path,
        min_connections=5,
        max_connections=20,
        read_only=False
    )
    await pool.initialize()

    engine = AsyncCortexEngine(pool=pool, db_path=db_path)

    yield engine

    await pool.close()


@pytest.mark.asyncio
async def test_pool_exhaustion_register_agent(async_engine: AsyncCortexEngine):
    """Verify concurrent `register_agent` calls do not leak or exhaust pool."""
    tasks = []
    # 50 concurrent requests against a pool sizes of 20
    for i in range(50):
        tasks.append(
            async_engine.register_agent(
                name=f"agent_stress_{i}",
                agent_type="test_swarm",
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Ensure no timeouts or locked databases escaped
    exceptions = [r for r in results if isinstance(r, Exception)]
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    successes = [r for r in results if isinstance(r, str)]  # agent_id
    assert len(successes) == 50

    # Assert pool health
    assert not async_engine._pool._pool.empty()
    assert async_engine._pool._active_count <= 20


@pytest.mark.asyncio
async def test_pool_exhaustion_vote_v10k(async_engine: AsyncCortexEngine):
    """Verify 10,000 concurrent votes do not exhaust the connection pool."""
    NUM_AGENTS = 10000
    fact_id = 1

    # Pre-register one fact
    async with async_engine.session() as conn:
        await conn.execute(
            "INSERT INTO facts (id, tenant_id, project, content) "
            "VALUES (?, 'default', 'stress', 'test_content')",
            (fact_id,)
        )
        await conn.commit()

    # Pre-register agents (we use a batch to speed up prep)
    # register_agent is relatively heavy, let's do it in smaller batches
    # or just insert directly for speed since we test POOL stability of VOTE
    async with async_engine.session() as conn:
        for i in range(NUM_AGENTS):
            agent_id = f"agent_{i}"
            await conn.execute(
                "INSERT INTO agents (id, name, agent_type, reputation_score) "
                "VALUES (?, ?, 'tester', 1.0)",
                (agent_id, agent_id)
            )
        await conn.commit()

    # The actual stress test: 10,000 concurrent votes
    tasks = []
    for i in range(NUM_AGENTS):
        tasks.append(
            async_engine.vote(
                fact_id=fact_id,
                agent=f"agent_{i}",
                value=1,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    exceptions = [r for r in results if isinstance(r, Exception)]
    if exceptions:
        for e in exceptions[:5]:  # Just show first few
            logger.error("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        pytest.fail(f"Caught {len(exceptions)} exceptions during 10k votes stress test")

    # Final Pool Stats
    logger.info(
        "Final Pool Stats - Active: %d, QSize: %d",
        async_engine._pool._active_count,
        async_engine._pool._pool.qsize()
    )

    # All connections should be returned to the pool
    assert async_engine._pool._pool.qsize() >= 5
    assert async_engine._pool._active_count == 0

