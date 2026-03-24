from __future__ import annotations

from pathlib import Path

import pytest

from cortex.database.pool import CortexConnectionPool
from cortex.database.schema import get_init_meta
from cortex.engine_async import AsyncCortexEngine
from cortex.migrations.core import run_migrations_async


@pytest.fixture(autouse=True)
def mock_local_embedder() -> None:
    """Override the global sync-engine embedder fixture for async auth tests."""
    return None


@pytest.fixture
async def async_engine(tmp_path: Path):
    db_path = tmp_path / "auth-flow.db"
    pool = CortexConnectionPool(
        str(db_path),
        min_connections=1,
        max_connections=1,
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

    engine = AsyncCortexEngine(pool=pool, db_path=str(db_path))
    try:
        yield engine
    finally:
        await pool.close()
