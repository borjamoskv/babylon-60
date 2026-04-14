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
async def test_deprecated_fact_disappears_from_current_reads_but_survives_historical_tx(
    engine: CortexEngine,
):
    fact_id = await engine.store(
        project="deprecated-read-path",
        content="Deprecated facts must disappear from current recall without corrupting history.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT tx_id FROM facts WHERE id = ?", (fact_id,))
        tx_id = (await cursor.fetchone())[0]

    assert await engine.deprecate(fact_id, reason="superseded", tenant_id="tenant-recall") is True

    recalled = await engine.recall(project="deprecated-read-path", tenant_id="tenant-recall")
    current_world_state = await engine.time_travel(tenant_id="tenant-recall")
    historical_world_state = await engine.time_travel(tenant_id="tenant-recall", tx_id=tx_id)
    history = await engine.history(project="deprecated-read-path", tenant_id="tenant-recall")

    assert recalled == []
    assert current_world_state == []
    assert len(historical_world_state) == 1
    assert historical_world_state[0]["id"] == fact_id
    assert historical_world_state[0]["tx_id"] == tx_id
    assert len(history) == 1
    assert history[0].id == fact_id


@pytest.mark.asyncio
async def test_history_as_of_exposes_only_the_temporally_valid_window(engine: CortexEngine):
    fact_id = await engine.store(
        project="history-as-of",
        content="Temporal audit should expose facts only inside their valid window.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )
    assert await engine.deprecate(fact_id, reason="superseded", tenant_id="tenant-recall") is True

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT created_at, valid_until FROM facts WHERE id = ?",
            (fact_id,),
        )
        created_at, valid_until = await cursor.fetchone()

    history_before_deprecation = await engine.history(
        project="history-as-of",
        tenant_id="tenant-recall",
        as_of=created_at,
    )
    history_at_deprecation = await engine.history(
        project="history-as-of",
        tenant_id="tenant-recall",
        as_of=valid_until,
    )
    current_state = await engine.reconstruct_state(
        "history-as-of",
        tenant_id="tenant-recall",
    )

    assert len(history_before_deprecation) == 1
    assert history_before_deprecation[0].id == fact_id
    assert history_at_deprecation == []
    assert current_state == []


@pytest.mark.asyncio
async def test_time_travel_at_deprecation_tx_excludes_fact_from_present_state(engine: CortexEngine):
    fact_id = await engine.store(
        project="time-travel-deprecation-edge",
        content="The deprecation transaction should already exclude the fact from reconstructed state.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    assert await engine.deprecate(fact_id, reason="superseded", tenant_id="tenant-recall") is True

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT MAX(id) FROM transactions WHERE tenant_id = ?",
            ("tenant-recall",),
        )
        deprecation_tx_id = (await cursor.fetchone())[0]

    travelled = await engine.time_travel(
        tenant_id="tenant-recall",
        tx_id=deprecation_tx_id,
    )
    reconstructed = await engine.reconstruct_state(
        "time-travel-deprecation-edge",
        tenant_id="tenant-recall",
        tx_id=deprecation_tx_id,
    )

    assert travelled == []
    assert reconstructed == []


@pytest.mark.asyncio
async def test_temporal_queries_reject_unknown_transaction_ids(engine: CortexEngine):
    await engine.store(
        project="missing-tx",
        content="Temporal queries must fail closed when the requested transaction does not exist.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
    )

    with pytest.raises(ValueError, match="Transaction 999999 not found"):
        await engine.reconstruct_state(
            "missing-tx",
            tenant_id="tenant-recall",
            tx_id=999999,
        )

    with pytest.raises(ValueError, match="Transaction 999999 not found"):
        await engine.time_travel(
            tenant_id="tenant-recall",
            tx_id=999999,
        )


@pytest.mark.asyncio
async def test_get_causal_chain_preserves_direction_and_depth(engine: CortexEngine):
    root_id = await engine.store(
        project="causal-chain",
        content="Root decision in the causal lineage.",
        tenant_id="tenant-recall",
        fact_type="decision",
        source="agent:test",
    )
    child_id = await engine.store(
        project="causal-chain",
        content="Derived consequence from the root decision.",
        tenant_id="tenant-recall",
        fact_type="decision",
        source="agent:test",
        parent_decision_id=root_id,
    )
    grandchild_id = await engine.store(
        project="causal-chain",
        content="Second-order consequence from the derived fact.",
        tenant_id="tenant-recall",
        fact_type="knowledge",
        source="agent:test",
        parent_decision_id=child_id,
    )

    downward = await engine.get_causal_chain(
        fact_id=root_id,
        direction="down",
        tenant_id="tenant-recall",
    )
    upward = await engine.get_causal_chain(
        fact_id=grandchild_id,
        direction="up",
        tenant_id="tenant-recall",
    )
    stats = await engine.stats(tenant_id="tenant-recall")

    assert [(fact.id, fact.causal_depth) for fact in downward] == [
        (root_id, 0),
        (child_id, 1),
        (grandchild_id, 2),
    ]
    assert [(fact.id, fact.causal_depth) for fact in upward] == [
        (grandchild_id, 0),
        (child_id, 1),
        (root_id, 2),
    ]
    assert stats["causal_facts"] == 2


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
