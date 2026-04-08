"""Integration tests for cortex.engine.store_mixin.StoreMixin.

Uses CortexEngine with a fresh temp database for realistic end-to-end coverage
of the store → deduplicate → deprecate → update pipeline.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Mark all tests in this module as slow (CortexEngine.init_db() takes ~10s per fixture)
# Run with: pytest -m slow   or skip with: pytest -m 'not slow'
pytestmark = pytest.mark.slow


@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database, close after test."""
    import os

    from cortex.engine import CortexEngine

    # Unblock tests from thermodynamic enforcement
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"

    db = str(tmp_path / "test_store.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()

    # Ensure causal_edges exists (AsyncCausalGraph.ensure_table is a safety check)
    from cortex.engine.causality import AsyncCausalGraph

    async with e.session() as conn:
        cg = AsyncCausalGraph(conn)
        await cg.ensure_table()

    yield e
    await e.close()

    # Cleanup
    if "CORTEX_SKIP_EXERGY_VALIDATION" in os.environ:
        del os.environ["CORTEX_SKIP_EXERGY_VALIDATION"]


# ─── Store ────────────────────────────────────────────────────────────


class TestStore:
    async def test_store_returns_fact_id(self, engine):
        fact_id = await engine.store(
            project="test",
            content="The sovereign ledger stores facts immutably.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        assert isinstance(fact_id, int)
        assert fact_id > 0

    async def test_store_auto_attests_high_rigor_fact_without_explicit_signature(self, engine):
        fact_id = await engine.store(
            project="test",
            content="Decision facts should be auto-attested before guard execution.",
            fact_type="decision",
            source="api",
        )

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
            row = await cursor.fetchone()

        from cortex.crypto import get_default_encrypter

        meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
        assert meta["zk_proof_mode"] == "engine-auto-attested"
        assert meta["zk_proof_attestor"] == "api"
        assert "agent_public_key" in meta
        assert "zk_proof_signature" in meta

    async def test_store_fails_closed_when_guard_pipeline_broken(self, engine):
        class BrokenPipeline:
            async def run_guards(self, *args, **kwargs):
                raise RuntimeError("guard subsystem unavailable")

        engine._guard_pipeline = BrokenPipeline()

        with pytest.raises(RuntimeError, match="GuardPipeline pre-store failed"):
            await engine.store(
                project="test",
                content="This should never persist.",
                fact_type="knowledge",
                source="agent:test_suite",
            )

        facts = await engine.get_all_active_facts(tenant_id="default", project="test")
        assert facts == []

    async def test_store_deduplication_returns_same_id(self, engine):
        """Exact structural hash dedup should return the same fact_id."""
        content = "Deduplication test content unique enough to avoid cross-test collision."
        id1 = await engine.store(
            project="test",
            content=content,
            fact_type="knowledge",
            source="agent:test_suite",
        )
        id2 = await engine.store(
            project="test",
            content=content,
            fact_type="knowledge",
            source="agent:test_suite",
        )
        assert id1 == id2

    async def test_store_different_content_different_ids(self, engine):
        id1 = await engine.store(
            project="test",
            content="Fact alpha for diff test.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        id2 = await engine.store(
            project="test",
            content="Fact beta for diff test.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        assert id1 != id2

    async def test_store_rejects_empty_content(self, engine):
        from cortex.engine.storage_guard import GuardViolation

        with pytest.raises((ValueError, TypeError, GuardViolation)):
            await engine.store(
                project="test",
                content="",
                fact_type="knowledge",
                source="agent:test_suite",
            )

    async def test_store_accepts_runtime_fact_proposal_with_matching_taint(self, engine):
        from cortex.crypto import get_default_encrypter
        from cortex.guards.taint import TaintEngine
        from cortex.utils.canonical import canonical_json

        runtime_payload = {"event": "after_step", "status": "ok"}
        canonical_payload = canonical_json(runtime_payload)
        payload_hash = hashlib.sha3_256(canonical_payload.encode("utf-8")).hexdigest()
        taint = TaintEngine.generate_taint("agent-1", "sess-1", canonical_payload)

        fact_id = await engine.store(
            project="test",
            content="[AGENT PROPOSAL] runtime fact proposal from agent-1",
            fact_type="idea",
            source="agent:agent-1",
            meta={
                "runtime_artifact_kind": "fact_proposal",
                "runtime_payload_hash": payload_hash,
                "runtime_artifact": runtime_payload,
                "taint": taint,
            },
        )

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
            row = await cursor.fetchone()

        assert row is not None
        assert row[0].startswith(get_default_encrypter().PREFIX)
        meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
        assert meta["runtime_payload_hash"] == payload_hash
        assert meta["taint"] == taint

    async def test_store_rejects_runtime_fact_proposal_with_mismatched_taint(self, engine):
        from cortex.guards.taint import TaintEngine
        from cortex.utils.canonical import canonical_json

        runtime_payload = {"event": "after_step", "status": "ok"}
        canonical_payload = canonical_json(runtime_payload)
        taint = TaintEngine.generate_taint("agent-1", "sess-1", canonical_payload)

        with pytest.raises(ValueError, match="CORTEX-TAINT digest mismatch"):
            await engine.store(
                project="test",
                content="[AGENT PROPOSAL] runtime fact proposal from agent-1",
                fact_type="idea",
                source="agent:agent-1",
                meta={
                    "runtime_artifact_kind": "fact_proposal",
                    "runtime_payload_hash": "wrong-payload-hash",
                    "runtime_artifact": runtime_payload,
                    "taint": taint,
                },
            )

    async def test_store_rejects_missing_required_taint(self, engine):
        with pytest.raises(ValueError, match="CORTEX-TAINT required for this write"):
            await engine.store(
                project="test",
                content="This write explicitly requires taint proof.",
                fact_type="knowledge",
                source="agent:test_suite",
                meta={"requires_taint_proof": True},
            )

    async def test_store_encrypts_metadata_at_rest(self, engine):
        from cortex.crypto import get_default_encrypter

        fact_id = await engine.store(
            project="test",
            content="Metadata should be encrypted at rest by the write path.",
            fact_type="knowledge",
            source="agent:test_suite",
            meta={"secret_key": "vault-123", "classification": "restricted"},
        )

        async with engine.session() as conn:
            cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
            row = await cursor.fetchone()

        assert row is not None
        assert isinstance(row[0], str)
        assert row[0].startswith(get_default_encrypter().PREFIX)

        meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
        assert meta is not None
        assert meta["secret_key"] == "vault-123"
        assert meta["classification"] == "restricted"


class TestTaintContract:
    async def test_store_rejects_runtime_fact_proposal_without_taint(self, engine):
        with pytest.raises(ValueError, match="CORTEX-TAINT required"):
            await engine.store(
                project="test",
                content="[AGENT PROPOSAL] agent_step proposal proposal-1 from agent-1",
                fact_type="idea",
                source="agent:agent-1",
                meta={
                    "runtime_artifact_kind": "fact_proposal",
                    "runtime_payload_hash": "abc123",
                },
            )

    async def test_store_rejects_runtime_tool_evidence_without_taint(self, engine):
        with pytest.raises(ValueError, match="CORTEX-TAINT required"):
            await engine.store(
                project="test",
                content="[TOOL EVIDENCE] search status=ok call=call-1",
                fact_type="knowledge",
                source="tool:search",
                meta={
                    "runtime_artifact_kind": "tool_evidence",
                    "runtime_input_hash": "input-hash-1",
                },
            )

    async def test_store_rejects_runtime_fact_proposal_with_invalid_taint(self, engine):
        from cortex.guards.taint import TaintEngine

        canonical_payload = '{"event":"after_step","status":"ok"}'
        bad_payload = '{"event":"after_step","status":"drifted"}'
        taint = TaintEngine.generate_taint("agent-1", "sess-1", bad_payload)

        with pytest.raises(ValueError, match="CORTEX-TAINT digest mismatch"):
            await engine.store(
                project="test",
                content="[AGENT PROPOSAL] agent_step proposal proposal-2 from agent-1",
                fact_type="idea",
                source="agent:agent-1",
                meta={
                    "runtime_artifact_kind": "fact_proposal",
                    "runtime_payload_hash": hashlib.sha3_256(
                        canonical_payload.encode("utf-8")
                    ).hexdigest(),
                    "taint": taint,
                },
            )

    async def test_store_accepts_runtime_fact_proposal_with_valid_taint(self, engine):
        from cortex.guards.taint import TaintEngine

        canonical_payload = '{"event":"after_step","status":"ok"}'
        taint = TaintEngine.generate_taint("agent-1", "sess-1", canonical_payload)

        fact_id = await engine.store(
            project="test",
            content="[AGENT PROPOSAL] agent_step proposal proposal-3 from agent-1",
            fact_type="idea",
            source="agent:agent-1",
            meta={
                "runtime_artifact_kind": "fact_proposal",
                "runtime_payload_hash": hashlib.sha3_256(
                    canonical_payload.encode("utf-8")
                ).hexdigest(),
                "taint": taint,
            },
        )

        assert fact_id > 0

    async def test_store_rejects_runtime_rejection_without_taint(self, engine):
        with pytest.raises(ValueError, match="CORTEX-TAINT required"):
            await engine.store(
                project="test",
                content="[RUNTIME REJECTION] runtime:runtime_retry tool timed out",
                fact_type="decision",
                source="agent:agent-1",
                meta={
                    "runtime_artifact_kind": "rejection",
                    "runtime_artifact_hash": "rejection-hash-1",
                },
            )

    async def test_store_accepts_runtime_decision_edge_with_valid_artifact_hash_taint(self, engine):
        from cortex.guards.taint import TaintEngine

        canonical_artifact = (
            '{"decision_id":"decision-1","edge_id":"edge-1","edge_type":"used_as_evidence",'
            '"fact_id":"fact-1","metadata":{},"project":"proj-a","tenant_id":"tenant-a"}'
        )
        artifact_hash = hashlib.sha3_256(canonical_artifact.encode("utf-8")).hexdigest()
        taint = TaintEngine.generate_taint("agent-1", "sess-1", canonical_artifact)

        fact_id = await engine.store(
            project="test",
            content="[DECISION EDGE] decision=decision-1 fact=fact-1 type=used_as_evidence",
            fact_type="decision",
            source="agent:runtime-sink",
            meta={
                "runtime_artifact_kind": "decision_edge",
                "runtime_artifact_hash": artifact_hash,
                "taint": taint,
            },
        )

        assert fact_id > 0


# ─── Store Many ───────────────────────────────────────────────────────


class TestStoreMany:
    async def test_store_many_returns_ids(self, engine):
        facts = [
            {
                "project": "batch",
                "content": f"Batch fact {i} for store_many.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            }
            for i in range(3)
        ]
        ids = await engine.store_many(facts)
        assert len(ids) == 3
        assert all(isinstance(i, int) and i > 0 for i in ids)

    async def test_store_many_empty_raises(self, engine):
        with pytest.raises(ValueError, match="empty"):
            await engine.store_many([])

    async def test_store_many_schedules_graph_after_commit(self, engine, monkeypatch):
        graph_mock = AsyncMock(return_value=(0, 0))
        monkeypatch.setattr("cortex.graph.process_fact_graph", graph_mock)

        facts = [
            {
                "project": "batch-graph",
                "content": f"Batch graph fact {i} includes Madrid and OpenAI.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            }
            for i in range(2)
        ]

        ids = await engine.store_many(facts)
        assert len(ids) == 2

        await asyncio.sleep(0.05)

        assert graph_mock.await_count == 2

    async def test_store_many_rolls_back_after_duplicate_fast_path_then_failure(self, engine):
        facts = [
            {
                "project": "batch-atomic",
                "content": "Atomic batch fact that is long enough to be valid.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            },
            {
                "project": "batch-atomic",
                "content": "Atomic batch fact that is long enough to be valid.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            },
            {
                "project": "batch-atomic",
                "content": "",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
            },
        ]

        with pytest.raises(Exception):
            await engine.store_many(facts)

        stored = await engine.get_all_active_facts(tenant_id="default", project="batch-atomic")
        assert stored == []


# ─── Deprecate ────────────────────────────────────────────────────────


class TestDeprecate:
    async def test_deprecate_existing_fact(self, engine):
        fact_id = await engine.store(
            project="test",
            content="Fact to deprecate.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        result = await engine.deprecate(fact_id, reason="test")
        assert result is True

    async def test_deprecate_nonexistent_false(self, engine):
        result = await engine.deprecate(999999, reason="missing")
        assert result is False

    async def test_deprecate_invalid_id_raises(self, engine):
        with pytest.raises(ValueError, match="Invalid"):
            await engine.deprecate(-1)


# ─── Update ───────────────────────────────────────────────────────────


class TestUpdate:
    async def test_update_creates_new_version(self, engine):
        original_id = await engine.store(
            project="test",
            content="Original content v1 for update.",
            fact_type="knowledge",
            source="agent:test_suite",
        )
        updated_id = await engine.update(
            original_id,
            content="Updated content v2.",
        )
        assert updated_id != original_id
        assert updated_id > original_id

    async def test_update_nonexistent_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            await engine.update(999999, content="ghost update")


# ─── Taint Integration ──────────────────────────────────────────────────


class TestTaintIntegration:
    async def test_deprecate_triggers_taint_propagation(self, engine):
        # 1. Create parent fact (C5)
        parent_id = await engine.store(
            project="test",
            content="Parent fact that will be deprecated.",
            fact_type="knowledge",
            source="agent:test_suite",
            confidence="C5",
        )

        # 2. Create child fact depending on parent (C5)
        # We need to manually add the causal edge if `store` doesn't do it automatically,
        # but store takes parent_decision_id. Wait, does `store` create EDGE_DERIVED_FROM?
        child_id = await engine.store(
            project="test",
            content="Child fact that depends on parent.",
            fact_type="knowledge",
            source="agent:test_suite",
            confidence="C5",
            parent_decision_id=parent_id,
        )

        # Let's make sure edge is created. The current store() might not map parent_decision_id to an edge.
        # Let's manually create EDGE_DERIVED_FROM just in case.
        from cortex.engine.causality import EDGE_DERIVED_FROM

        async with engine.session() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO causal_edges (fact_id, parent_id, edge_type) VALUES (?, ?, ?)",
                    (child_id, parent_id, EDGE_DERIVED_FROM),
                )
                await conn.commit()

        # 3. Deprecate the parent fact. This should trigger propagate_taint.
        await engine.deprecate(parent_id, reason="testing taint propagation")

        # 4. Check the child's confidence. Invalidation triggers propagate_taint,
        # which downgrades the confidence. If parent goes C5 -> None, child goes C5 -> C4 (or lower based on logic).
        child_fact = await engine.get_fact(child_id)
        assert child_fact is not None, "Child fact should exist"
        assert child_fact.confidence != "C5", (
            "Child confidence should be downgraded upon parent invalidation"
        )
        # Check that it's marked as tainted in causal_edges
        from cortex.engine.causality import EDGE_TAINTED_BY

        async with engine.session() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND edge_type = ?",
                    (parent_id, EDGE_TAINTED_BY),
                )
                taint_edges = await cur.fetchall()
                taint_sources = [row[0] for row in taint_edges]
                assert child_id in taint_sources, (
                    "Child should be linked by EDGE_TAINTED_BY to the deprecated parent"
                )

    async def test_invalidate_triggers_taint_propagation(self, engine):
        # 1. Create parent fact
        parent_id = await engine.store(
            project="test",
            content="Evil parent fact.",
            fact_type="knowledge",
            source="agent:test_suite",
            confidence="C5",
        )

        # 2. Create child fact
        child_id = await engine.store(
            project="test",
            content="Innocent child fact.",
            fact_type="knowledge",
            source="agent:test_suite",
            confidence="C5",
        )

        from cortex.engine.causality import EDGE_DERIVED_FROM, EDGE_TAINTED_BY

        async with engine.session() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO causal_edges (fact_id, parent_id, edge_type) VALUES (?, ?, ?)",
                    (child_id, parent_id, EDGE_DERIVED_FROM),
                )
                await conn.commit()

        # 3. Invalidate the parent
        await engine.invalidate(parent_id, reason="testing invalidation taint")

        # 4. Check the parent fact (should be C1 and tombstoned -- tombstone might remove it from get_fact if it filters status, let's see)
        async with engine.session() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT confidence, is_tombstoned FROM facts WHERE id = ?", (parent_id,)
                )
                p_row = await cur.fetchone()
                assert p_row is not None
                assert p_row[0] == "C1", "Parent confidence should be C1 after invalidate"
                assert p_row[1] == 1, "Parent should be tombstoned"

                await cur.execute("SELECT confidence FROM facts WHERE id = ?", (child_id,))
                c_row = await cur.fetchone()
                assert c_row is not None
                assert c_row[0] == "C4", "Child confidence should be downgraded to C4"

                await cur.execute(
                    "SELECT fact_id FROM causal_edges WHERE parent_id = ? AND edge_type = ?",
                    (parent_id, EDGE_TAINTED_BY),
                )
                taint_edges = await cur.fetchall()
                taint_sources = [row[0] for row in taint_edges]
                assert child_id in taint_sources, "Child should have TAINTED_BY edge"
