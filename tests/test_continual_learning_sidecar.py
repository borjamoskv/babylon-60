"""Tests for the continual-learning sidecar MVP."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pytest

from cortex.extensions.continual_learning import (
    AdapterLifecycleAction,
    LearningThresholds,
    LifelongLearningSidecar,
    LoRAConfig,
    MicroUpdateBackendResult,
    agem_project,
    compute_cfs,
    schedule_learning_rate,
)
from cortex.extensions.continual_learning.sidecar import (
    InMemoryPrototypeStore,
    InMemorySemanticMemoryStore,
    ListRetrainQueue,
)


@dataclass
class DummyTagger:
    """Static tagging hook for deterministic tests."""

    payload: dict[str, object]

    def tag(self, text: str) -> dict[str, object]:
        return dict(self.payload)


class DummyEmbedder:
    """Small deterministic embedder for unit tests."""

    def embed(self, text: str) -> tuple[float, ...]:
        digest = hashlib.sha3_256(text.encode("utf-8")).digest()
        return tuple(
            float(int.from_bytes(digest[index : index + 4], "big")) for index in range(0, 16, 4)
        )


class StaticBackend:
    """Static micro-update backend for deterministic execution tests."""

    def __init__(self, result_factory):
        self._result_factory = result_factory
        self.calls = []

    def execute(self, plan):
        self.calls.append(plan)
        return self._result_factory(plan)


def make_sidecar(
    *,
    now: float = 1_000.0,
    tagger_payload: dict[str, object] | None = None,
    thresholds: LearningThresholds | None = None,
) -> tuple[LifelongLearningSidecar, list[float]]:
    """Create a sidecar plus a mutable clock holder."""
    current = [now]
    sidecar = LifelongLearningSidecar(
        embedder=DummyEmbedder(),
        tagger=DummyTagger(
            tagger_payload
            or {
                "domain": "support",
                "intent": "answer",
                "confidence": 0.9,
                "novelty": 1.0,
            }
        ),
        thresholds=thresholds,
        lora_config=LoRAConfig(),
        prototype_store=InMemoryPrototypeStore(),
        semantic_store=InMemorySemanticMemoryStore(),
        retrain_queue=ListRetrainQueue(),
        clock=lambda: current[0],
    )
    return sidecar, current


def test_on_interaction_sanitizes_and_preserves_tenant_isolation() -> None:
    sidecar, _ = make_sidecar()

    experience = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Contact me at user@example.com",
        trace_id="trace-1",
    )

    assert "[EMAIL_ADDRESS]" in experience.text
    assert "user@example.com" not in experience.text
    assert experience.tenant_id == "tenant-a"
    assert sidecar.buffer.sample(tenant_id="tenant-a", domain="support", k=1)[0].id == experience.id
    assert sidecar.buffer.sample(tenant_id="tenant-b", domain="support", k=1) == ()


def test_buffer_deduplicates_semantically_and_keeps_highest_priority() -> None:
    sidecar, _ = make_sidecar()

    first = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Reset my password",
        trace_id="trace-1",
    )
    second = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-2",
        text="Reset my password",
        trace_id="trace-2",
    )

    sampled = sidecar.buffer.sample(tenant_id="tenant-a", domain="support", k=10)
    assert len(sampled) == 1
    assert sampled[0].id == first.id
    assert second.id != first.id


def test_buffer_ttl_and_capacity_preserve_pinned_anchor() -> None:
    thresholds = LearningThresholds(default_ttl_seconds=10, default_max_buffer_items=2)
    sidecar, clock = make_sidecar(thresholds=thresholds)

    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Pinned anchor",
        trace_id="anchor-1",
        metadata={"pinned_anchor": True},
    )
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-2",
        text="Low priority example",
        trace_id="low-1",
        metadata={"confidence": 0.4, "novelty": 0.5},
    )
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-3",
        text="High priority example",
        trace_id="high-1",
        metadata={"confidence": 0.95, "novelty": 1.2},
    )

    sampled = sidecar.buffer.sample(tenant_id="tenant-a", domain=None, k=10)
    trace_ids = {item.trace_id for item in sampled}
    assert "anchor-1" in trace_ids
    assert "high-1" in trace_ids
    assert "low-1" not in trace_ids

    clock[0] += 20
    assert sidecar.buffer.sample(tenant_id="tenant-a", domain=None, k=10) == ()


def test_make_mixed_batch_uses_rehearsal_split_and_prototypes() -> None:
    sidecar, _ = make_sidecar()
    prototype_store = sidecar._prototype_store  # noqa: SLF001 - deterministic test setup

    for idx in range(12):
        experience = sidecar.on_interaction(
            tenant_id="tenant-a",
            user_id=f"user-{idx}",
            text=f"Support example {idx}",
            trace_id=f"trace-{idx}",
            metadata={"pinned_anchor": idx < 3},
        )
        if idx < 5:
            prototype_store.add("tenant-a", "support", [experience])

    batch = sidecar.make_mixed_batch(tenant_id="tenant-a", domain="support")

    assert len(batch.new_examples) == 8
    assert len(batch.anchor_examples) == 3
    assert len(batch.prototype_examples) == 5


def test_plan_micro_update_decreases_learning_rate_with_risk() -> None:
    low_risk_sidecar, _ = make_sidecar(
        tagger_payload={
            "domain": "support",
            "intent": "answer",
            "confidence": 0.95,
            "novelty": 1.0,
            "cost_of_error": 0.1,
        }
    )
    high_risk_sidecar, _ = make_sidecar(
        tagger_payload={
            "domain": "support",
            "intent": "answer",
            "confidence": 0.2,
            "novelty": 1.0,
            "cost_of_error": 5.0,
        }
    )

    low_risk_sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Low risk interaction",
    )
    high_risk_sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="High risk interaction",
    )

    low_plan = low_risk_sidecar.plan_micro_update(tenant_id="tenant-a", domain="support")
    high_plan = high_risk_sidecar.plan_micro_update(tenant_id="tenant-a", domain="support")

    assert low_plan.learning_rate > high_plan.learning_rate
    assert low_plan.risk_score < high_plan.risk_score


def test_agem_projection_removes_negative_interference() -> None:
    projected = agem_project([1.0, -2.0], [1.0, 1.0])

    assert np.dot(projected, np.asarray([1.0, 1.0])) >= -1e-8


def test_evaluate_update_uses_critical_threshold_and_cfs() -> None:
    sidecar, _ = make_sidecar()

    summary = sidecar.evaluate_update(
        before_scores={"security": 0.90, "support": 0.80},
        after_scores={"security": 0.87, "support": 0.78},
        critical_domains={"security"},
    )

    assert summary.rollback_required is True
    assert summary.cfs == pytest.approx(
        compute_cfs({"security": 0.90, "support": 0.80}, {"security": 0.87, "support": 0.78})
    )
    assert "security" in summary.reason


def test_manage_adapters_requires_sustained_drift_before_child_creation() -> None:
    sidecar, _ = make_sidecar()
    baseline = [(0.0, 0.0), (0.1, 0.1), (0.2, 0.2)]
    current = [(5.0, 5.0), (5.2, 5.1), (5.4, 5.3)]

    decision_1 = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=baseline,
        current_embeddings=current,
        metrics={"delta_f1": -0.01},
    )
    decision_2 = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=baseline,
        current_embeddings=current,
        metrics={"delta_f1": -0.01},
    )
    decision_3 = sidecar.manage_adapters(
        tenant_id="tenant-a",
        domain="support",
        baseline_embeddings=baseline,
        current_embeddings=current,
        metrics={"delta_f1": -0.01},
    )

    assert decision_1.action is AdapterLifecycleAction.NOOP
    assert decision_2.action is AdapterLifecycleAction.NOOP
    assert decision_3.action is AdapterLifecycleAction.CREATE_CHILD
    assert decision_3.drift_signal is not None
    assert decision_3.drift_signal.consecutive_breaches == 3


def test_status_reports_scoped_buffer_and_adapter_state() -> None:
    sidecar, _ = make_sidecar()
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Support example",
        trace_id="trace-1",
    )
    plan = sidecar.plan_micro_update(tenant_id="tenant-a", domain="support")
    sidecar.registry.snapshot(
        adapter_id=plan.adapter_id,
        reason="baseline",
        metrics={"f1": 0.91},
    )

    status = sidecar.status(tenant_id="tenant-a", domain="support")

    assert status["enabled"] is True
    assert status["tenant_id"] == "tenant-a"
    assert status["domain"] == "support"
    assert status["buffer_items"] == 1
    assert status["active_adapter_id"] == plan.adapter_id
    assert status["snapshot_count"] == 1
    assert status["known_domains"] == ["support"]


def test_execute_micro_update_commits_and_resets_rollback_streak() -> None:
    sidecar, _ = make_sidecar()
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Support example",
        trace_id="trace-1",
        metadata={"feedback": "Use the reset flow"},
    )
    sidecar.registry.get_or_create_active_adapter(
        tenant_id="tenant-a",
        domain="support",
        base_model_id="frozen-base",
        rank_r=16,
    )
    active_adapter = sidecar.registry.get_active_adapter("tenant-a", "support")
    assert active_adapter is not None
    sidecar.registry.snapshot(
        adapter_id=active_adapter,
        reason="known_good",
        metrics={"support": 0.8},
        path_weights="/tmp/base.safetensors",
    )
    sidecar.registry.rollback(active_adapter)
    assert sidecar.registry.rollback_streak("tenant-a", "support") == 1

    backend = StaticBackend(
        lambda plan: MicroUpdateBackendResult(
            adapter_id=plan.adapter_id,
            before_scores={"support": 0.80},
            after_scores={"support": 0.86},
            training_metrics={"delta_f1": 0.06},
            artifact_path="/tmp/adapter_v2.safetensors",
            backend_name="test-backend",
            snapshot_reason="post_test_execution",
        )
    )

    execution = sidecar.execute_micro_update(
        tenant_id="tenant-a",
        domain="support",
        backend=backend,
    )

    assert execution.committed is True
    assert execution.rollback_decision.action is AdapterLifecycleAction.NOOP
    assert execution.lifecycle_decision.action is AdapterLifecycleAction.NOOP
    assert sidecar.registry.rollback_streak("tenant-a", "support") == 0
    assert sidecar.registry.get_state(active_adapter).path_weights == "/tmp/adapter_v2.safetensors"  # type: ignore[union-attr]


def test_execute_micro_update_rolls_back_to_previous_snapshot_on_regression() -> None:
    sidecar, _ = make_sidecar()
    sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="Support example",
        trace_id="trace-1",
        metadata={"feedback": "Use the reset flow"},
    )
    adapter_id = sidecar.registry.get_or_create_active_adapter(
        tenant_id="tenant-a",
        domain="support",
        base_model_id="frozen-base",
        rank_r=16,
    )
    sidecar.registry.update_artifact(
        adapter_id,
        path_weights="/tmp/known_good.safetensors",
        status="trained",
    )
    sidecar.registry.snapshot(
        adapter_id=adapter_id,
        reason="known_good",
        metrics={"support": 0.90},
        path_weights="/tmp/known_good.safetensors",
    )

    backend = StaticBackend(
        lambda plan: MicroUpdateBackendResult(
            adapter_id=plan.adapter_id,
            before_scores={"support": 0.90},
            after_scores={"support": 0.80},
            training_metrics={"delta_f1": -0.10},
            artifact_path="/tmp/bad_update.safetensors",
            backend_name="test-backend",
        )
    )

    execution = sidecar.execute_micro_update(
        tenant_id="tenant-a",
        domain="support",
        backend=backend,
    )

    state = sidecar.registry.get_state(adapter_id)
    assert execution.committed is False
    assert execution.rollback_decision.action is AdapterLifecycleAction.ROLLBACK
    assert execution.lifecycle_decision.action is AdapterLifecycleAction.NOOP
    assert state is not None
    assert state.path_weights == "/tmp/known_good.safetensors"
    assert sidecar.registry.rollback_streak("tenant-a", "support") == 1


def test_forget_purges_non_parametric_memory_and_enqueues_retrain() -> None:
    sidecar, _ = make_sidecar()
    semantic_store = sidecar._semantic_store  # noqa: SLF001 - deterministic test setup
    retrain_queue = sidecar._retrain_queue  # noqa: SLF001 - deterministic test setup
    prototype_store = sidecar._prototype_store  # noqa: SLF001 - deterministic test setup

    experience = sidecar.on_interaction(
        tenant_id="tenant-a",
        user_id="user-1",
        text="secret token 123",
        trace_id="trace-secret",
    )
    semantic_store.add("tenant-a", "chunk-1", "secret token 123 in semantic store")
    prototype_store.add("tenant-a", "support", [experience])

    result = sidecar.forget(
        tenant_id="tenant-a",
        user_id="user-1",
        query="secret token",
    )

    assert experience.id in result["deleted_exp_ids"]
    assert result["deleted_chunk_ids"] == ["chunk-1"]
    assert result["deleted_prototypes"] == 1
    assert retrain_queue.items[0]["type"] == "retrain_from_clean_snapshot"


def test_schedule_learning_rate_returns_risk_score() -> None:
    low_lr, low_risk = schedule_learning_rate(5e-5, 0.95, 0.1)
    high_lr, high_risk = schedule_learning_rate(5e-5, 0.1, 10.0, policy_violation=True)

    assert low_lr > 0
    assert high_lr > 0
    assert low_risk < high_risk
    assert low_lr > high_lr
