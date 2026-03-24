from __future__ import annotations

import os
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.extensions.security.tenant import tenant_id_var


@pytest.fixture
async def engine(tmp_path: Path):
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    db_path = tmp_path / "ledger-isolation.db"
    eng = CortexEngine(db_path=str(db_path), auto_embed=False)
    await eng.init_db()
    try:
        yield eng
    finally:
        await eng.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)


@pytest.mark.asyncio
async def test_ledger_chain_and_reconstruction_are_tenant_scoped(engine: CortexEngine) -> None:
    token_a = tenant_id_var.set("tenant_a")
    try:
        await engine.store(
            project="shared-project",
            content="tenant-a fact",
            fact_type="knowledge",
            source="test-suite",
        )
    finally:
        tenant_id_var.reset(token_a)

    token_b = tenant_id_var.set("tenant_b")
    try:
        await engine.store(
            project="shared-project",
            content="tenant-b fact",
            fact_type="knowledge",
            source="test-suite",
        )
    finally:
        tenant_id_var.reset(token_b)

    async with engine.session() as conn:
        async with conn.execute(
            "SELECT id, tenant_id, prev_hash FROM transactions WHERE action = 'store' ORDER BY id ASC"
        ) as cursor:
            tx_rows = await cursor.fetchall()

    tx_by_tenant = {row[1]: row for row in tx_rows}
    assert tx_by_tenant["tenant_a"][2] == "GENESIS"
    assert tx_by_tenant["tenant_b"][2] == "GENESIS"

    facts_a = await engine.reconstruct_state(
        "shared-project",
        tenant_id="tenant_a",
        tx_id=tx_by_tenant["tenant_a"][0],
    )
    facts_b = await engine.reconstruct_state(
        "shared-project",
        tenant_id="tenant_b",
        tx_id=tx_by_tenant["tenant_b"][0],
    )

    assert [fact["content"] for fact in facts_a] == ["tenant-a fact"]
    assert [fact["content"] for fact in facts_b] == ["tenant-b fact"]

    with pytest.raises(ValueError):
        await engine.reconstruct_state(
            "shared-project",
            tenant_id="tenant_a",
            tx_id=tx_by_tenant["tenant_b"][0],
        )
