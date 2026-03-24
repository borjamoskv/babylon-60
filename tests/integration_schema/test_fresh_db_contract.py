from __future__ import annotations

import os
from pathlib import Path

import pytest

from cortex.engine import CortexEngine


def _facts_columns(rows: list[tuple]) -> set[str]:
    return {row[1] for row in rows}


@pytest.mark.asyncio
async def test_fresh_db_exposes_canonical_facts_contract(tmp_path: Path) -> None:
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    db_path = tmp_path / "fresh-contract.db"
    engine = CortexEngine(db_path=str(db_path), auto_embed=False)

    try:
        await engine.init_db()

        parent_id = await engine.store(
            project="schema-contract",
            content="parent decision for canonical schema contract",
            fact_type="decision",
            source="test-suite",
        )
        child_id = await engine.store(
            project="schema-contract",
            content="child fact for canonical schema contract",
            fact_type="knowledge",
            source="test-suite",
            meta={"cognitive_layer": "episodic"},
            parent_decision_id=parent_id,
        )

        child = await engine.get_fact(child_id, tenant_id="default")
        assert child is not None
        assert child.tx_id is not None
        assert child.cognitive_layer == "episodic"
        assert child.parent_decision_id == parent_id

        async with engine.session() as conn:
            async with conn.execute("PRAGMA table_info(facts)") as cursor:
                columns = _facts_columns(await cursor.fetchall())
            async with conn.execute(
                """
                SELECT tx_id, cognitive_layer, parent_decision_id
                FROM facts
                WHERE id = ?
                """,
                (child_id,),
            ) as cursor:
                stored = await cursor.fetchone()

        assert {"tx_id", "cognitive_layer", "parent_decision_id", "consensus_score", "last_accessed"} <= columns
        assert stored is not None
        assert stored[0] is not None
        assert stored[1] == "episodic"
        assert stored[2] == parent_id
    finally:
        await engine.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)
