"""Persistence tests for the continual-learning sidecar."""

from __future__ import annotations

from pathlib import Path

from cortex.extensions.continual_learning import (
    AdapterLifecycleAction,
    AdapterRegistry,
    LifelongLearningSidecar,
    PrioritizedEpisodicBuffer,
    SQLiteContinualLearningStore,
    SQLitePrototypeStore,
    SQLiteRetrainQueue,
    SQLiteSemanticMemoryStore,
)
from tests.test_continual_learning_sidecar import DummyEmbedder, DummyTagger


def make_persistent_sidecar(
    tmp_path: Path,
) -> tuple[LifelongLearningSidecar, SQLiteContinualLearningStore]:
    """Create a sidecar backed by a temporary SQLite store."""
    store = SQLiteContinualLearningStore(tmp_path / "continual_learning.db")
    sidecar = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        prototype_store=SQLitePrototypeStore(store),
        semantic_store=SQLiteSemanticMemoryStore(store),
        retrain_queue=SQLiteRetrainQueue(store),
        registry=AdapterRegistry(persistence=store),
        buffer=PrioritizedEpisodicBuffer(
            max_items=50_000,
            ttl_seconds=72 * 3600,
            dedup_tau=0.92,
            persistence=store,
        ),
    )
    return sidecar, store


def test_sidecar_rehydrates_buffer_and_prototypes_from_sqlite(tmp_path: Path) -> None:
    sidecar, store = make_persistent_sidecar(tmp_path)

    experience = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Persist me",
        trace_id="trace-1",
    )
    sidecar._prototype_store.add("tenant-a", "support", [experience])  # noqa: SLF001

    restored = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        prototype_store=SQLitePrototypeStore(store),
        semantic_store=SQLiteSemanticMemoryStore(store),
        retrain_queue=SQLiteRetrainQueue(store),
        registry=AdapterRegistry(persistence=store),
        buffer=PrioritizedEpisodicBuffer(
            max_items=50_000,
            ttl_seconds=72 * 3600,
            dedup_tau=0.92,
            persistence=store,
        ),
    )

    sampled = restored.buffer.sample(tenant_id="tenant-a", domain="support", k=1)
    assert sampled[0].trace_id == "trace-1"
    batch = restored.make_mixed_batch(tenant_id="tenant-a", domain="support")
    assert batch.prototype_examples[0].id == experience.id


def test_sidecar_preserves_injected_empty_persistent_buffer(tmp_path: Path) -> None:
    """An empty injected buffer must not be replaced by an ephemeral default buffer."""
    store = SQLiteContinualLearningStore(tmp_path / "continual_learning.db")
    persistent_buffer = PrioritizedEpisodicBuffer(
        max_items=50_000,
        ttl_seconds=72 * 3600,
        dedup_tau=0.92,
        persistence=store,
    )

    sidecar = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        prototype_store=SQLitePrototypeStore(store),
        semantic_store=SQLiteSemanticMemoryStore(store),
        retrain_queue=SQLiteRetrainQueue(store),
        registry=AdapterRegistry(persistence=store),
        buffer=persistent_buffer,
    )

    assert sidecar.buffer is persistent_buffer
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Persist me",
        trace_id="trace-1",
    )
    assert len(store.load_buffer_entries()) == 1


def test_sidecar_rehydrates_adapters_and_snapshots_from_sqlite(tmp_path: Path) -> None:
    sidecar, store = make_persistent_sidecar(tmp_path)

    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Trigger planning",
        trace_id="trace-1",
    )
    plan = sidecar.plan_micro_update(tenant_id="tenant-a", domain="support")
    sidecar.registry.snapshot(
        adapter_id=plan.adapter_id,
        reason="baseline",
        metrics={"f1": 0.91},
    )
    decision = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=[(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)],
        current_embeddings=[(5.0, 5.0), (5.1, 5.2), (5.3, 5.4)],
        metrics={"delta_f1": -0.02},
    )
    decision = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=[(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)],
        current_embeddings=[(5.0, 5.0), (5.1, 5.2), (5.3, 5.4)],
        metrics={"delta_f1": -0.02},
    )
    decision = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=[(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)],
        current_embeddings=[(5.0, 5.0), (5.1, 5.2), (5.3, 5.4)],
        metrics={"delta_f1": -0.02},
    )
    assert decision.action is AdapterLifecycleAction.CREATE_CHILD

    restored = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        prototype_store=SQLitePrototypeStore(store),
        semantic_store=SQLiteSemanticMemoryStore(store),
        retrain_queue=SQLiteRetrainQueue(store),
        registry=AdapterRegistry(persistence=store),
        buffer=PrioritizedEpisodicBuffer(
            max_items=50_000,
            ttl_seconds=72 * 3600,
            dedup_tau=0.92,
            persistence=store,
        ),
    )

    active_adapter = restored.registry.get_active_adapter("tenant-a", "support")
    assert active_adapter == decision.adapter_id


def test_forget_persists_deletions_and_retrain_jobs(tmp_path: Path) -> None:
    sidecar, store = make_persistent_sidecar(tmp_path)
    semantic_store = sidecar._semantic_store  # noqa: SLF001
    prototype_store = sidecar._prototype_store  # noqa: SLF001

    experience = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="secret memory",
        trace_id="trace-secret",
    )
    semantic_store.add("tenant-a", "chunk-secret", "secret memory in semantic store")
    prototype_store.add("tenant-a", "support", [experience])

    result = sidecar.forget(tenant_id="tenant-a", user_id="user-1", query="secret")
    assert experience.id in result["deleted_exp_ids"]

    restored = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        prototype_store=SQLitePrototypeStore(store),
        semantic_store=SQLiteSemanticMemoryStore(store),
        retrain_queue=SQLiteRetrainQueue(store),
        registry=AdapterRegistry(persistence=store),
        buffer=PrioritizedEpisodicBuffer(
            max_items=50_000,
            ttl_seconds=72 * 3600,
            dedup_tau=0.92,
            persistence=store,
        ),
    )

    assert restored.buffer.sample(tenant_id="tenant-a", domain="support", k=10) == ()
    assert restored._retrain_queue.items[0]["query"] == "secret"  # noqa: SLF001
