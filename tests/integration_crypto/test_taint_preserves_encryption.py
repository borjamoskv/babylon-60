from __future__ import annotations

import aiosqlite
import pytest

from cortex.crypto import get_default_encrypter
from cortex.database.schema import CREATE_FACTS, CREATE_TRANSACTIONS
from cortex.database.schema_extensions import CREATE_ENTITY_EVENTS
from cortex.engine.causality import EDGE_DERIVED_FROM, AsyncCausalGraph
from cortex.engine.mutation_engine import MUTATION_ENGINE


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation_method", ["deprecate", "invalidate"])
async def test_taint_preserves_encryption_and_tenant_bounds(mutation_method: str) -> None:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(CREATE_FACTS)
    await conn.execute(CREATE_TRANSACTIONS)
    await conn.execute(CREATE_ENTITY_EVENTS)

    graph = AsyncCausalGraph(conn)
    await graph.ensure_table()

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    shared_project = "shared-project"
    enc = get_default_encrypter()

    try:
        source_meta_raw = enc.encrypt_json({"secret": "parent"}, tenant_id=tenant_a)
        child_a_meta_raw = enc.encrypt_json(
            {"previous_fact_id": 1, "secret": "child-a"},
            tenant_id=tenant_a,
        )
        child_b_meta_raw = enc.encrypt_json(
            {"previous_fact_id": 1, "secret": "child-b"},
            tenant_id=tenant_b,
        )

        await conn.executemany(
            """
            INSERT INTO facts (
                id, tenant_id, project, content, fact_type, metadata, confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            [
                (
                    1,
                    tenant_a,
                    shared_project,
                    "Parent fact whose lineage becomes untrusted after review.",
                    "knowledge",
                    source_meta_raw,
                    "C5",
                ),
                (
                    2,
                    tenant_a,
                    shared_project,
                    "Derived child fact that should be tainted and re-encrypted.",
                    "knowledge",
                    child_a_meta_raw,
                    "C5",
                ),
                (
                    3,
                    tenant_b,
                    shared_project,
                    "Other tenant child that must never be tainted by tenant_a.",
                    "knowledge",
                    child_b_meta_raw,
                    "C5",
                ),
            ],
        )
        await conn.executemany(
            """
            INSERT INTO causal_edges (fact_id, parent_id, edge_type, project, tenant_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (2, 1, EDGE_DERIVED_FROM, shared_project, tenant_a),
                (3, 1, EDGE_DERIVED_FROM, shared_project, tenant_b),
            ],
        )

        if mutation_method == "deprecate":
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=1,
                tenant_id=tenant_a,
                event_type="deprecate",
                payload={"reason": "regression-test", "timestamp": "2026-03-24T00:00:00+00:00"},
                signer="tests",
                commit=False,
            )
        else:
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=1,
                tenant_id=tenant_a,
                event_type="tombstone",
                payload={"reason": "regression-test", "timestamp": "2026-03-24T00:00:00+00:00"},
                signer="tests",
                commit=False,
            )
            await MUTATION_ENGINE.apply(
                conn,
                fact_id=1,
                tenant_id=tenant_a,
                event_type="score_update",
                payload={"confidence": "C1", "consensus_score": 0.0},
                signer="tests",
                commit=False,
            )

        report = await graph.propagate_taint(1, tenant_id=tenant_a)
        await conn.commit()

        assert report.affected_count == 1

        async with conn.execute(
            "SELECT metadata FROM facts WHERE id = ? AND tenant_id = ?",
            (1, tenant_a),
        ) as cursor:
            source_row = await cursor.fetchone()
        async with conn.execute(
            "SELECT confidence, metadata FROM facts WHERE id = ? AND tenant_id = ?",
            (2, tenant_a),
        ) as cursor:
            child_a_row = await cursor.fetchone()
        async with conn.execute(
            "SELECT confidence, metadata FROM facts WHERE id = ? AND tenant_id = ?",
            (3, tenant_b),
        ) as cursor:
            child_b_row = await cursor.fetchone()

        assert source_row is not None
        assert child_a_row is not None
        assert child_b_row is not None

        source_meta_after = source_row[0]
        child_a_confidence, child_a_meta_after = child_a_row
        child_b_confidence, child_b_meta_after = child_b_row

        assert source_meta_after.startswith("v6_aesgcm:")
        assert child_a_meta_after.startswith("v6_aesgcm:")
        assert child_b_meta_after.startswith("v6_aesgcm:")

        source_meta = enc.decrypt_json(source_meta_after, tenant_id=tenant_a)
        child_a_meta = enc.decrypt_json(child_a_meta_after, tenant_id=tenant_a)
        child_b_meta = enc.decrypt_json(child_b_meta_after, tenant_id=tenant_b)

        assert source_meta == {"secret": "parent"}
        assert child_a_confidence == "C4"
        assert child_a_meta is not None
        assert child_a_meta["secret"] == "child-a"
        assert child_a_meta["previous_fact_id"] == 1
        assert child_a_meta["tainted_by"] == 1
        assert "taint_timestamp" in child_a_meta

        assert child_b_confidence == "C5"
        assert child_b_meta is not None
        assert child_b_meta["secret"] == "child-b"
        assert child_b_meta["previous_fact_id"] == 1
        assert "tainted_by" not in child_b_meta
    finally:
        await conn.close()
