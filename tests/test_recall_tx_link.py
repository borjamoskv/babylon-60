"""Regression tests for transaction linkage on the recall read-path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.engine.guard_pipeline import GuardPipeline

pytestmark = pytest.mark.slow


@pytest.fixture
async def engine(tmp_path: Path):
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"

    db_path = str(tmp_path / "recall_tx_link.db")
    engine = CortexEngine(db_path=db_path, auto_embed=False)
    engine._guard_pipeline = GuardPipeline()
    await engine.init_db()

    yield engine

    await engine.close()
    os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)


@pytest.mark.asyncio
async def test_engine_recall_preserves_fact_transaction_link(engine: CortexEngine):
    fact_id = await engine.store(
        project="recall-tx-link",
        content="Facts recalled from the read path must preserve their ledger linkage.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT tx_id FROM facts WHERE id = ?", (fact_id,))
        tx_id = (await cursor.fetchone())[0]

    recalled = await engine.recall(project="recall-tx-link", tenant_id="tenant-recall")

    assert len(recalled) == 1
    assert recalled[0]["id"] == fact_id
    assert recalled[0]["tx_id"] == tx_id


@pytest.mark.asyncio
async def test_fact_manager_recall_preserves_fact_transaction_link(engine: CortexEngine):
    fact_id = await engine.store(
        project="recall-tx-link-manager",
        content="FactManager recall should surface tx_id on the model as well.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT tx_id FROM facts WHERE id = ?", (fact_id,))
        tx_id = (await cursor.fetchone())[0]

    recalled = await engine.facts.recall(
        project="recall-tx-link-manager",
        tenant_id="tenant-recall",
    )

    assert len(recalled) == 1
    assert recalled[0].id == fact_id
    assert recalled[0].tx_id == tx_id


@pytest.mark.asyncio
async def test_reconstruct_state_round_trips_through_transaction_timestamp(engine: CortexEngine):
    fact_id = await engine.store(
        project="reconstruct-state",
        content="Reconstruction anchored to tx_id must resolve the ledger timestamp correctly.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT tx_id FROM facts WHERE id = ?", (fact_id,))
        tx_id = (await cursor.fetchone())[0]

    reconstructed = await engine.reconstruct_state(
        "reconstruct-state",
        tenant_id="tenant-recall",
        tx_id=tx_id,
    )
    travelled = await engine.time_travel(
        tenant_id="tenant-recall",
        tx_id=tx_id,
    )
    ledger_report = await engine.verify_ledger()

    assert len(reconstructed) == 1
    assert reconstructed[0]["id"] == fact_id
    assert reconstructed[0]["tx_id"] == tx_id
    assert len(travelled) == 1
    assert travelled[0]["id"] == fact_id
    assert travelled[0]["tx_id"] == tx_id
    assert ledger_report["valid"] is True
    assert ledger_report["tx_count"] >= 1
