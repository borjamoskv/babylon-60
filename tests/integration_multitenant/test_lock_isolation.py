from __future__ import annotations

from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.engine.lock import SovereignLock


@pytest.fixture
async def engine(tmp_path: Path):
    db_path = tmp_path / "lock-isolation.db"
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    await eng.init_db()
    try:
        yield eng
    finally:
        await eng.close()


@pytest.mark.asyncio
async def test_same_resource_can_be_locked_by_two_tenants(engine: CortexEngine) -> None:
    tenant_a_lock = SovereignLock(engine, tenant_id="tenant_a")
    tenant_b_lock = SovereignLock(engine, tenant_id="tenant_b")

    assert await tenant_a_lock.acquire("shared-resource", "agent-a", timeout_s=1.0)
    assert await tenant_b_lock.acquire("shared-resource", "agent-b", timeout_s=1.0)

    async with engine.session() as conn:
        async with conn.execute(
            "SELECT tenant_id, resource, holder_agent FROM lock_state ORDER BY tenant_id"
        ) as cursor:
            rows = await cursor.fetchall()

    assert rows == [
        ("tenant_a", "shared-resource", "agent-a"),
        ("tenant_b", "shared-resource", "agent-b"),
    ]

    await tenant_a_lock.release("shared-resource", "agent-a")
    assert await tenant_b_lock.is_locked("shared-resource") is True

    await tenant_b_lock.release("shared-resource", "agent-b")
    assert await tenant_a_lock.is_locked("shared-resource") is False
    assert await tenant_b_lock.is_locked("shared-resource") is False
