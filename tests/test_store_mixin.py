"""Integration tests for cortex.engine.store_mixin.StoreMixin.

Uses CortexEngine with a fresh temp database for realistic end-to-end coverage
of the store → deduplicate → deprecate → update pipeline.
"""

from __future__ import annotations

import sqlite3
import urllib.error
from pathlib import Path

import aiosqlite
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

    async def test_fact_manager_store_contract_keeps_int_api_unless_opted_in(self, engine):
        plain_id = await engine.facts.store(
            project="test",
            content="FactManager direct store should still expose a plain fact identifier.",
            fact_type="knowledge",
            source="agent:test_suite",
        )

        created_id, created = await engine.facts.store(
            project="test",
            content="FactManager can opt into created state when the batch bridge needs it.",
            fact_type="knowledge",
            source="agent:test_suite",
            _return_created=True,
        )
        dedup_id, dedup_created = await engine.facts.store(
            project="test",
            content="FactManager can opt into created state when the batch bridge needs it.",
            fact_type="knowledge",
            source="agent:test_suite",
            _return_created=True,
        )

        assert isinstance(plain_id, int)
        assert isinstance(created_id, int)
        assert created is True
        assert dedup_id == created_id
        assert dedup_created is False

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

    async def test_store_rolls_back_when_precommit_post_hook_fails(self, engine):
        class BrokenPipeline:
            async def run_guards(self, *args, **kwargs):
                return None

            async def run_post_hooks(self, *args, **kwargs):
                if kwargs.get("after_commit") is False:
                    raise RuntimeError("ledger checkpoint unavailable")
                return None

        engine._guard_pipeline = BrokenPipeline()

        with pytest.raises(RuntimeError, match="GuardPipeline post-hooks failed"):
            await engine.store(
                project="test",
                content="This write must not survive a failed pre-commit hook.",
                fact_type="knowledge",
                source="agent:test_suite",
            )

        facts = await engine.get_all_active_facts(tenant_id="default", project="test")
        assert facts == []

        with sqlite3.connect(engine._db_path) as fresh_conn:
            persisted = fresh_conn.execute(
                "SELECT COUNT(*) FROM facts WHERE tenant_id = ? AND project = ?",
                ("default", "test"),
            ).fetchone()[0]
        assert persisted == 0

    async def test_store_fails_closed_when_contradiction_scan_db_error(self, engine, monkeypatch):
        from cortex.guards import contradiction_guard as module

        class FailingConn:
            row_factory = None

            async def execute(self, *args, **kwargs):
                raise aiosqlite.OperationalError("db unavailable")

        class FailingCtx:
            async def __aenter__(self):
                return FailingConn()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(module, "connect_async_ctx", lambda _path: FailingCtx())

        with pytest.raises(RuntimeError, match="GuardPipeline pre-store failed"):
            await engine.store(
                project="test",
                content="Decision facts must not persist when contradiction scanning cannot complete.",
                fact_type="decision",
                source="agent:test_suite",
            )

        facts = await engine.get_all_active_facts(tenant_id="default", project="test")
        assert facts == []

    async def test_store_rejects_external_script_when_sri_fetch_fails(self, engine, monkeypatch):
        from cortex.engine.membrane import sri_hash

        def fail_urlopen(*args, **kwargs):
            raise urllib.error.URLError("network down")

        sri_hash.generate_sri_hash.cache_clear()
        monkeypatch.setattr(sri_hash.urllib.request, "urlopen", fail_urlopen)

        with pytest.raises(ValueError, match="External resource rejected by SRI membrane"):
            await engine.store(
                project="test",
                content='<script src="https://cdn.jsdelivr.net/npm/lib.js"></script>',
                fact_type="knowledge",
                source="agent:test_suite",
            )

        facts = await engine.get_all_active_facts(tenant_id="default", project="test")
        assert facts == []

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

    async def test_store_many_runs_precommit_and_after_commit_hooks_for_each_created_fact(
        self, engine
    ):
        class TrackingPipeline:
            def __init__(self) -> None:
                self.events: list[tuple[bool | None, str, int]] = []

            async def run_guards(self, *args, **kwargs):
                return None

            async def run_post_hooks(self, fact_id, project, fact_type, conn, **kwargs):
                self.events.append((kwargs.get("after_commit"), kwargs["tenant_id"], fact_id))

        tracking = TrackingPipeline()
        engine._guard_pipeline = tracking

        facts = [
            {
                "project": "batch-hooks",
                "content": "Batch hook fact alpha long enough to persist safely.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
                "tenant_id": "tenant-batch",
            },
            {
                "project": "batch-hooks",
                "content": "Batch hook fact beta long enough to persist safely.",
                "fact_type": "knowledge",
                "source": "agent:test_suite",
                "tenant_id": "tenant-batch",
            },
        ]

        ids = await engine.store_many(facts)

        assert [phase for phase, _, _ in tracking.events] == [False, False, True, True]
        assert [tenant_id for _, tenant_id, _ in tracking.events] == ["tenant-batch"] * 4
        assert [fact_id for phase, _, fact_id in tracking.events if phase is False] == ids
        assert [fact_id for phase, _, fact_id in tracking.events if phase is True] == ids

    async def test_store_many_skips_hooks_for_deduped_facts(self, engine):
        class TrackingPipeline:
            def __init__(self) -> None:
                self.events: list[tuple[bool | None, int]] = []

            async def run_guards(self, *args, **kwargs):
                return None

            async def run_post_hooks(self, fact_id, project, fact_type, conn, **kwargs):
                self.events.append((kwargs.get("after_commit"), fact_id))

        tracking = TrackingPipeline()
        engine._guard_pipeline = tracking

        ids = await engine.store_many(
            [
                {
                    "project": "batch-dedup-hooks",
                    "content": "Batch dedup fact alpha long enough to persist safely.",
                    "fact_type": "knowledge",
                    "source": "agent:test_suite",
                },
                {
                    "project": "batch-dedup-hooks",
                    "content": "Batch dedup fact alpha long enough to persist safely.",
                    "fact_type": "knowledge",
                    "source": "agent:test_suite",
                },
            ]
        )

        assert ids[0] == ids[1]
        assert tracking.events == [(False, ids[0]), (True, ids[0])]

    async def test_store_many_rolls_back_when_precommit_hook_fails(self, engine):
        class BrokenPipeline:
            async def run_guards(self, *args, **kwargs):
                return None

            async def run_post_hooks(self, *args, **kwargs):
                if kwargs.get("after_commit") is False:
                    raise RuntimeError("ledger checkpoint unavailable")
                return None

        engine._guard_pipeline = BrokenPipeline()

        with pytest.raises(RuntimeError, match="ledger checkpoint unavailable"):
            await engine.store_many(
                [
                    {
                        "project": "batch-hook-rollback",
                        "content": "This batch write must roll back on a pre-commit hook failure.",
                        "fact_type": "knowledge",
                        "source": "agent:test_suite",
                        "tenant_id": "tenant-batch",
                    },
                    {
                        "project": "batch-hook-rollback",
                        "content": "Second batch write should not survive a failed pre-commit hook.",
                        "fact_type": "knowledge",
                        "source": "agent:test_suite",
                        "tenant_id": "tenant-batch",
                    },
                ]
            )

        stored = await engine.get_all_active_facts(
            tenant_id="tenant-batch",
            project="batch-hook-rollback",
        )
        assert stored == []

        with sqlite3.connect(engine._db_path) as fresh_conn:
            persisted = fresh_conn.execute(
                "SELECT COUNT(*) FROM facts WHERE tenant_id = ? AND project = ?",
                ("tenant-batch", "batch-hook-rollback"),
            ).fetchone()[0]
        assert persisted == 0


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

        active = await engine.get_all_active_facts(tenant_id="default", project="test")
        assert [fact.id for fact in active] == []

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

    async def test_update_rolls_back_if_replacement_store_fails(self, engine):
        original_id = await engine.store(
            project="test",
            content="Original content that must survive a failed update.",
            fact_type="knowledge",
            source="agent:test_suite",
        )

        class BrokenPipeline:
            async def run_guards(self, *args, **kwargs):
                raise RuntimeError("guard subsystem unavailable")

        engine._guard_pipeline = BrokenPipeline()

        with pytest.raises(RuntimeError, match="GuardPipeline pre-store failed"):
            await engine.update(
                original_id,
                content="Updated content that should never persist.",
            )

        with sqlite3.connect(engine._db_path) as fresh_conn:
            row = fresh_conn.execute(
                "SELECT valid_until, is_tombstoned FROM facts WHERE id = ?",
                (original_id,),
            ).fetchone()
            count = fresh_conn.execute(
                "SELECT COUNT(*) FROM facts WHERE project = ?",
                ("test",),
            ).fetchone()[0]

        assert row == (None, 0)
        assert count == 1


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
