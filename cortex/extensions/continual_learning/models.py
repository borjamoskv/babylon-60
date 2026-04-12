"""Typed contracts for the continual-learning sidecar.

The sidecar keeps the frozen base model out of the write path and moves
online adaptation into a deterministic control layer: prioritized replay,
adapter lifecycle management, drift gating, and rollback policy.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

__all__ = [
    "AdapterDecision",
    "AdapterLifecycleAction",
    "MicroUpdateBackend",
    "MicroUpdateBackendResult",
    "MicroUpdateExecution",
    "AdapterSnapshot",
    "AdapterState",
    "AuditSink",
    "DriftSignal",
    "Embedder",
    "EvaluationSummary",
    "ExperienceRecord",
    "BufferPersistence",
    "LearningThresholds",
    "LoRAConfig",
    "MergeBackend",
    "MicroUpdatePlan",
    "MixedBatch",
    "AdapterPersistence",
    "PrototypeStore",
    "RetrainQueue",
    "SemanticMemoryStore",
    "Tagger",
]


def _require_non_blank(name: str, value: str) -> str:
    """Validate and normalize non-blank string inputs."""
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-blank")
    return normalized


def _normalize_embedding(embedding: Sequence[float] | None) -> tuple[float, ...]:
    """Normalize embeddings into an immutable tuple."""
    if embedding is None:
        return ()
    return tuple(float(value) for value in embedding)


@dataclass(frozen=True)
class ExperienceRecord:
    """Sanitized interaction captured by the continual-learning sidecar."""

    id: str
    tenant_id: str
    user_id: str
    ts: float
    domain: str
    intent: str
    text: str
    confidence: float
    priority: float
    cost_of_error: float | None = None
    reward: float | None = None
    feedback: str | None = None
    embedding: tuple[float, ...] = field(default_factory=tuple)
    semantic_hash: str = ""
    ttl_deadline: float | None = None
    trace_id: str = ""
    pii_categories: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    adapter_id: str | None = None

    def __post_init__(self) -> None:
        """Enforce invariants at creation time."""
        object.__setattr__(self, "tenant_id", _require_non_blank("tenant_id", self.tenant_id))
        object.__setattr__(self, "user_id", _require_non_blank("user_id", self.user_id))
        object.__setattr__(self, "domain", _require_non_blank("domain", self.domain))
        object.__setattr__(self, "intent", _require_non_blank("intent", self.intent))
        object.__setattr__(self, "text", self.text.strip())
        object.__setattr__(self, "trace_id", self.trace_id.strip())
        object.__setattr__(self, "embedding", _normalize_embedding(self.embedding))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "pii_categories", tuple(sorted(self.pii_categories)))

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.priority < 0.0:
            raise ValueError("priority must be >= 0.0")
        if self.cost_of_error is not None and self.cost_of_error < 0.0:
            raise ValueError("cost_of_error must be >= 0.0")


@dataclass(frozen=True)
class MixedBatch:
    """Balanced rehearsal batch for a single micro-update."""

    new_examples: tuple[ExperienceRecord, ...] = field(default_factory=tuple)
    anchor_examples: tuple[ExperienceRecord, ...] = field(default_factory=tuple)
    prototype_examples: tuple[ExperienceRecord, ...] = field(default_factory=tuple)

    @property
    def all_examples(self) -> tuple[ExperienceRecord, ...]:
        """Return the flattened batch contents."""
        return self.new_examples + self.anchor_examples + self.prototype_examples

    @property
    def size(self) -> int:
        """Return the total number of examples across all sources."""
        return len(self.all_examples)


@dataclass(frozen=True)
class LoRAConfig:
    """Control-plane defaults for adapter-only online updates."""

    rank_r: int = 16
    base_learning_rate: float = 5e-5
    batch_size: int = 32
    new_examples: int = 8
    anchor_examples: int = 16
    prototype_examples: int = 8
    min_learning_rate_scale: float = 0.2
    max_learning_rate_scale: float = 1.0
    base_model_id: str = "frozen-base"

    def __post_init__(self) -> None:
        """Validate configuration ranges."""
        if self.rank_r <= 0:
            raise ValueError("rank_r must be > 0")
        if self.base_learning_rate <= 0.0:
            raise ValueError("base_learning_rate must be > 0.0")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if self.new_examples < 0 or self.anchor_examples < 0 or self.prototype_examples < 0:
            raise ValueError("rehearsal splits must be >= 0")
        if self.min_learning_rate_scale <= 0.0:
            raise ValueError("min_learning_rate_scale must be > 0.0")
        if self.max_learning_rate_scale < self.min_learning_rate_scale:
            raise ValueError("max_learning_rate_scale must be >= min_learning_rate_scale")
        object.__setattr__(
            self, "base_model_id", _require_non_blank("base_model_id", self.base_model_id)
        )


@dataclass(frozen=True)
class LearningThresholds:
    """Guardrail thresholds for rollback, forgetting, and drift gating."""

    critical_rollback_pct: float = 0.02
    non_critical_rollback_pct: float = 0.05
    cfs_suspend_threshold: float = 0.05
    drift_psi_threshold: float = 0.2
    drift_ks_p_threshold: float = 0.01
    sustained_windows: int = 3
    dedup_tau: float = 0.92
    default_ttl_seconds: int = 72 * 3600
    default_max_buffer_items: int = 50_000
    rollback_streak_limit: int = 3

    def __post_init__(self) -> None:
        """Validate threshold ranges."""
        for name in (
            "critical_rollback_pct",
            "non_critical_rollback_pct",
            "cfs_suspend_threshold",
            "drift_psi_threshold",
            "drift_ks_p_threshold",
            "dedup_tau",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        if self.sustained_windows <= 0:
            raise ValueError("sustained_windows must be > 0")
        if self.default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be > 0")
        if self.default_max_buffer_items <= 0:
            raise ValueError("default_max_buffer_items must be > 0")
        if self.rollback_streak_limit <= 0:
            raise ValueError("rollback_streak_limit must be > 0")


@dataclass(frozen=True)
class MicroUpdatePlan:
    """Deterministic micro-update plan emitted by the sidecar."""

    tenant_id: str
    domain: str
    adapter_id: str
    learning_rate: float
    risk_score: float
    batch: MixedBatch

    def __post_init__(self) -> None:
        """Validate plan invariants."""
        object.__setattr__(self, "tenant_id", _require_non_blank("tenant_id", self.tenant_id))
        object.__setattr__(self, "domain", _require_non_blank("domain", self.domain))
        object.__setattr__(self, "adapter_id", _require_non_blank("adapter_id", self.adapter_id))
        if self.learning_rate <= 0.0:
            raise ValueError("learning_rate must be > 0.0")
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class MicroUpdateBackendResult:
    """Structured outcome returned by an external micro-update backend."""

    adapter_id: str
    before_scores: dict[str, float]
    after_scores: dict[str, float]
    training_metrics: dict[str, float] = field(default_factory=dict)
    baseline_embeddings: tuple[tuple[float, ...], ...] = field(default_factory=tuple)
    current_embeddings: tuple[tuple[float, ...], ...] = field(default_factory=tuple)
    artifact_path: str = ""
    data_fingerprint: str = ""
    backend_name: str = ""
    snapshot_reason: str = "post_micro_update"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize backend outputs."""
        object.__setattr__(self, "adapter_id", _require_non_blank("adapter_id", self.adapter_id))
        object.__setattr__(self, "artifact_path", self.artifact_path.strip())
        object.__setattr__(self, "data_fingerprint", self.data_fingerprint.strip())
        object.__setattr__(self, "backend_name", self.backend_name.strip())
        object.__setattr__(
            self, "snapshot_reason", self.snapshot_reason.strip() or "post_micro_update"
        )
        object.__setattr__(self, "before_scores", dict(self.before_scores))
        object.__setattr__(self, "after_scores", dict(self.after_scores))
        object.__setattr__(self, "training_metrics", dict(self.training_metrics))
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(
            self,
            "baseline_embeddings",
            tuple(_normalize_embedding(embedding) for embedding in self.baseline_embeddings),
        )
        object.__setattr__(
            self,
            "current_embeddings",
            tuple(_normalize_embedding(embedding) for embedding in self.current_embeddings),
        )
        if not self.before_scores:
            raise ValueError("before_scores must not be empty")
        if not self.after_scores:
            raise ValueError("after_scores must not be empty")


@dataclass(frozen=True)
class MicroUpdateExecution:
    """End-to-end execution result for a planned continual-learning update."""

    plan: MicroUpdatePlan
    backend_result: MicroUpdateBackendResult
    evaluation: EvaluationSummary
    rollback_decision: AdapterDecision
    lifecycle_decision: AdapterDecision
    committed: bool


@dataclass(frozen=True)
class DriftSignal:
    """Drift score computed over a tenant/domain embedding window."""

    psi: float
    ks_statistic: float
    ks_p_value: float
    breached: bool
    consecutive_breaches: int
    sample_size: int


@dataclass(frozen=True)
class EvaluationSummary:
    """Regression gate output for a proposed adapter update."""

    before_scores: dict[str, float]
    after_scores: dict[str, float]
    delta_by_domain: dict[str, float]
    cfs: float
    rollback_required: bool
    suspend_learning: bool
    reason: str = ""


class AdapterLifecycleAction(str, Enum):
    """Valid lifecycle actions the adapter control plane can emit."""

    NOOP = "noop"
    CREATE_CHILD = "create_child"
    FUSE = "fuse"
    ROLLBACK = "rollback"
    ARCHIVE = "archive"


@dataclass(frozen=True)
class AdapterSnapshot:
    """Immutable adapter checkpoint used for rollback and replay."""

    snapshot_id: str
    adapter_id: str
    created_at: float
    metrics: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    pii_clean: bool = True
    rollback_candidate: bool = True
    path_weights: str = ""
    data_fingerprint: str = ""


@dataclass
class AdapterState:
    """Mutable registry view of a single adapter."""

    adapter_id: str
    tenant_id: str
    domain: str
    base_model_id: str
    rank_r: int
    created_at: float
    status: str = "active"
    last_used_at: float | None = None
    parent_adapter_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    drift_stats: dict[str, float] = field(default_factory=dict)
    rollback_to_snapshot_id: str | None = None
    path_weights: str = ""


@dataclass(frozen=True)
class AdapterDecision:
    """Decision emitted by adapter lifecycle management."""

    action: AdapterLifecycleAction
    adapter_id: str | None
    reason: str
    drift_signal: DriftSignal | None = None
    metrics: dict[str, float] = field(default_factory=dict)


class AuditSink(Protocol):
    """Optional audit sink used to record sidecar state changes."""

    def emit(self, event_type: str, tenant_id: str, payload: dict[str, Any]) -> None:
        """Emit a sidecar audit event."""
        ...


class Tagger(Protocol):
    """Domain tagging hook used during ingestion."""

    def tag(self, text: str) -> dict[str, Any]:
        """Infer domain, intent, confidence, and optional novelty metadata."""
        ...


class Embedder(Protocol):
    """Embedding hook used for deduplication and drift windows."""

    def embed(self, text: str) -> Sequence[float]:
        """Return a dense embedding for sanitized text."""
        ...


class BufferPersistence(Protocol):
    """Persistence hook for replay-buffer state."""

    def load_buffer_entries(self) -> Sequence[dict[str, Any]]:
        """Return serialized buffer entries to hydrate on startup."""
        ...

    def save_buffer_entry(self, payload: dict[str, Any]) -> None:
        """Persist a serialized buffer entry."""
        ...

    def delete_buffer_entries(self, experience_ids: Sequence[str]) -> None:
        """Delete one or more serialized buffer entries."""
        ...


class AdapterPersistence(Protocol):
    """Persistence hook for adapter registry state."""

    def load_adapter_states(self) -> Sequence[dict[str, Any]]:
        """Return serialized adapter states."""
        ...

    def load_active_scopes(self) -> dict[tuple[str, str], str]:
        """Return active adapter identifiers keyed by ``(tenant_id, domain)``."""
        ...

    def load_adapter_snapshots(self) -> Sequence[dict[str, Any]]:
        """Return serialized adapter snapshots."""
        ...

    def load_rollback_streaks(self) -> dict[tuple[str, str], int]:
        """Return rollback streak counters keyed by ``(tenant_id, domain)``."""
        ...

    def save_adapter_state(self, payload: dict[str, Any]) -> None:
        """Persist a serialized adapter state."""
        ...

    def save_active_scope(self, tenant_id: str, domain: str, adapter_id: str) -> None:
        """Persist the active adapter mapping for a scope."""
        ...

    def save_adapter_snapshot(self, payload: dict[str, Any]) -> None:
        """Persist a serialized adapter snapshot."""
        ...

    def increment_rollback_streak(self, tenant_id: str, domain: str) -> int:
        """Increase and return the rollback streak for a scope."""
        ...

    def reset_rollback_streak(self, tenant_id: str, domain: str) -> None:
        """Reset the rollback streak for a scope after a successful execution."""
        ...


class PrototypeStore(Protocol):
    """Prototype source used to compact old examples for rehearsal."""

    def add(self, tenant_id: str, domain: str, examples: Sequence[ExperienceRecord]) -> None:
        """Persist examples as prototype candidates for a tenant/domain."""
        ...

    def sample(self, tenant_id: str, domain: str, k: int) -> Sequence[ExperienceRecord]:
        """Return up to ``k`` prototypes for the requested scope."""
        ...

    def purge_by_source_ids(self, source_ids: Sequence[str]) -> int:
        """Delete prototypes derived from the supplied example identifiers."""
        ...


class SemanticMemoryStore(Protocol):
    """Non-parametric memory store used by selective forgetting."""

    def delete_by_query(self, tenant_id: str, query: str) -> list[str]:
        """Delete semantically indexed chunks matching ``query``."""
        ...


class RetrainQueue(Protocol):
    """Queue used to request replay from a clean adapter snapshot."""

    def put(self, job: dict[str, Any]) -> None:
        """Push a replay job onto the retraining queue."""
        ...


class MergeBackend(Protocol):
    """Optional backend for adapter fusion operations."""

    def merge_into(self, adapter_name: str, method: str, density: float) -> str:
        """Fuse adapters and return the path or identifier of the merged artifact."""
        ...


class MicroUpdateBackend(Protocol):
    """External trainer that executes an adapter-only micro-update."""

    def execute(self, plan: MicroUpdatePlan) -> MicroUpdateBackendResult:
        """Train the adapter for ``plan`` and return structured evaluation outputs."""
        ...
