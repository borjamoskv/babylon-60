"""Minimal continual-learning sidecar for CORTEX 6.

This module implements the deterministic control plane around online
adapter updates:

- prioritized episodic replay with semantic deduplication and TTL
- conservative micro-update planning for frozen-base + LoRA adapters
- drift-triggered adapter lifecycle actions
- rollback gating via per-domain regressions and CFS
- selective forgetting for non-parametric memory plus replay requests
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from cortex.extensions.continual_learning.algorithms import (
    centroid_distance_projection,
    compute_cfs,
    compute_priority,
    cosine_similarity,
    ks_2samp,
    population_stability_index,
    schedule_learning_rate,
    stable_text_hash,
)
from cortex.extensions.continual_learning.models import (
    AdapterDecision,
    AdapterLifecycleAction,
    AdapterPersistence,
    AdapterSnapshot,
    AdapterState,
    AuditSink,
    BufferPersistence,
    DriftSignal,
    Embedder,
    EvaluationSummary,
    ExperienceRecord,
    LearningThresholds,
    LoRAConfig,
    MergeBackend,
    MicroUpdateBackend,
    MicroUpdateExecution,
    MicroUpdatePlan,
    MixedBatch,
    PrototypeStore,
    RetrainQueue,
    SemanticMemoryStore,
    Tagger,
)
from cortex.memory.pii_sanitizer import PIISanitizer

__all__ = [
    "AdapterRegistry",
    "DriftTracker",
    "InMemoryPrototypeStore",
    "InMemorySemanticMemoryStore",
    "ListRetrainQueue",
    "LifelongLearningSidecar",
    "NoOpAuditSink",
    "PrioritizedEpisodicBuffer",
]

logger = logging.getLogger("cortex.extensions.continual_learning")


@dataclass
class _BufferEntry:
    """Internal buffer wrapper retaining replay metadata."""

    experience: ExperienceRecord
    priority: float
    inserted_at: float
    last_seen_at: float
    novelty: float
    pinned_anchor: bool
    dedup_group_id: str


class NoOpAuditSink:
    """Default audit sink used when ledger integration is not yet wired."""

    def emit(self, event_type: str, tenant_id: str, payload: dict[str, Any]) -> None:
        """Drop events while keeping a uniform call site."""
        logger.debug(
            "continual_learning audit=%s tenant=%s payload=%s", event_type, tenant_id, payload
        )


class InMemoryPrototypeStore:
    """Simple in-memory prototype store for deterministic tests and local runs."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], list[ExperienceRecord]] = defaultdict(list)

    def add(self, tenant_id: str, domain: str, examples: Sequence[ExperienceRecord]) -> None:
        """Append prototype candidates for a tenant/domain."""
        key = (tenant_id.strip(), domain.strip())
        self._items[key].extend(examples)

    def sample(self, tenant_id: str, domain: str, k: int) -> Sequence[ExperienceRecord]:
        """Return the most recent prototypes for the requested scope."""
        key = (tenant_id.strip(), domain.strip())
        return tuple(self._items.get(key, [])[: max(k, 0)])

    def purge_by_source_ids(self, source_ids: Sequence[str]) -> int:
        """Delete prototypes that originated from deleted examples."""
        source_set = set(source_ids)
        deleted = 0
        for key, items in list(self._items.items()):
            kept = [item for item in items if item.id not in source_set]
            deleted += len(items) - len(kept)
            self._items[key] = kept
        return deleted


class InMemorySemanticMemoryStore:
    """Minimal semantic store used to exercise selective forgetting flows."""

    def __init__(self) -> None:
        self._chunks: dict[str, list[dict[str, str]]] = defaultdict(list)

    def add(self, tenant_id: str, chunk_id: str, text: str) -> None:
        """Store a chunk for later delete-by-query tests."""
        self._chunks[tenant_id.strip()].append({"chunk_id": chunk_id, "text": text})

    def delete_by_query(self, tenant_id: str, query: str) -> list[str]:
        """Delete chunks whose text contains the supplied query."""
        tenant_key = tenant_id.strip()
        needle = query.lower().strip()
        deleted: list[str] = []
        kept: list[dict[str, str]] = []
        for chunk in self._chunks.get(tenant_key, []):
            if needle and needle in chunk["text"].lower():
                deleted.append(chunk["chunk_id"])
            else:
                kept.append(chunk)
        self._chunks[tenant_key] = kept
        return deleted


class ListRetrainQueue:
    """List-backed queue recorder for replay requests."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def put(self, job: dict[str, Any]) -> None:
        """Append a replay job."""
        self.items.append(dict(job))


class PrioritizedEpisodicBuffer:
    """Tenant-scoped prioritized replay buffer with TTL and semantic deduplication."""

    def __init__(
        self,
        *,
        max_items: int,
        ttl_seconds: int,
        dedup_tau: float,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], float] | None = None,
        persistence: BufferPersistence | None = None,
    ) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be > 0")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        if not 0.0 <= dedup_tau <= 1.0:
            raise ValueError("dedup_tau must be between 0.0 and 1.0")

        self._max_items = max_items
        self._ttl_seconds = ttl_seconds
        self._dedup_tau = dedup_tau
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._clock = clock or time.time
        self._persistence = persistence
        self._entries: dict[str, _BufferEntry] = {}
        self._hydrate()

    def __len__(self) -> int:
        """Return the number of live buffer entries."""
        self._evict_expired()
        return len(self._entries)

    def add(
        self,
        experience: ExperienceRecord,
        *,
        novelty: float = 1.0,
        pinned_anchor: bool = False,
    ) -> str:
        """Insert or merge an experience into the buffer."""
        self._evict_expired()

        duplicate_id = self._find_duplicate(experience)
        now = self._clock()
        if duplicate_id is not None:
            existing = self._entries[duplicate_id]
            existing.priority = max(existing.priority, experience.priority)
            existing.last_seen_at = now
            existing.pinned_anchor = existing.pinned_anchor or pinned_anchor
            self._persist_entry(existing)
            self._audit_sink.emit(
                "buffer.deduplicated",
                experience.tenant_id,
                {
                    "experience_id": duplicate_id,
                    "trace_id": experience.trace_id,
                    "priority": existing.priority,
                },
            )
            return duplicate_id

        dedup_group_id = experience.semantic_hash or stable_text_hash(experience.text)
        self._entries[experience.id] = _BufferEntry(
            experience=experience,
            priority=experience.priority,
            inserted_at=now,
            last_seen_at=now,
            novelty=max(novelty, 0.0),
            pinned_anchor=pinned_anchor,
            dedup_group_id=dedup_group_id,
        )
        self._persist_entry(self._entries[experience.id])
        self._audit_sink.emit(
            "buffer.inserted",
            experience.tenant_id,
            {
                "experience_id": experience.id,
                "domain": experience.domain,
                "trace_id": experience.trace_id,
                "pinned_anchor": pinned_anchor,
            },
        )
        self._evict_over_capacity()
        return experience.id

    def sample(
        self,
        *,
        tenant_id: str,
        domain: str | None,
        k: int,
        anchors_only: bool = False,
        high_priority: bool = True,
    ) -> tuple[ExperienceRecord, ...]:
        """Sample up to ``k`` examples, always preserving tenant isolation."""
        if k <= 0:
            return ()

        self._evict_expired()
        tenant_key = tenant_id.strip()
        domain_key = domain.strip() if domain is not None else None

        candidates = [
            entry
            for entry in self._entries.values()
            if entry.experience.tenant_id == tenant_key
            and (domain_key is None or entry.experience.domain == domain_key)
            and (not anchors_only or entry.pinned_anchor)
        ]
        if not candidates and anchors_only:
            candidates = [
                entry
                for entry in self._entries.values()
                if entry.experience.tenant_id == tenant_key
            ]

        if high_priority:
            candidates.sort(
                key=lambda entry: (entry.priority, entry.novelty, entry.last_seen_at),
                reverse=True,
            )
        else:
            candidates.sort(key=lambda entry: entry.last_seen_at, reverse=True)
        return tuple(entry.experience for entry in candidates[:k])

    def delete_by_query(self, *, tenant_id: str, query: str) -> list[str]:
        """Delete matching experiences from the buffer."""
        self._evict_expired()
        tenant_key = tenant_id.strip()
        needle = query.lower().strip()
        deleted_ids: list[str] = []
        for experience_id, entry in list(self._entries.items()):
            if entry.experience.tenant_id != tenant_key:
                continue
            haystacks = [entry.experience.text.lower(), entry.experience.trace_id.lower()]
            if needle and any(needle in haystack for haystack in haystacks):
                deleted_ids.append(experience_id)
                del self._entries[experience_id]
        if deleted_ids and self._persistence is not None:
            self._persistence.delete_buffer_entries(tuple(deleted_ids))

        if deleted_ids:
            self._audit_sink.emit(
                "buffer.deleted",
                tenant_key,
                {"experience_ids": deleted_ids, "query": query},
            )
        return deleted_ids

    def embeddings_for_scope(
        self, *, tenant_id: str, domain: str | None
    ) -> list[tuple[float, ...]]:
        """Return embeddings for the requested scope."""
        self._evict_expired()
        tenant_key = tenant_id.strip()
        domain_key = domain.strip() if domain is not None else None
        return [
            entry.experience.embedding
            for entry in self._entries.values()
            if entry.experience.tenant_id == tenant_key
            and (domain_key is None or entry.experience.domain == domain_key)
            and entry.experience.embedding
        ]

    def _find_duplicate(self, experience: ExperienceRecord) -> str | None:
        """Find an existing semantically equivalent experience in the same tenant."""
        if not experience.embedding:
            return None
        for existing_id, entry in self._entries.items():
            if entry.experience.tenant_id != experience.tenant_id:
                continue
            if not entry.experience.embedding:
                continue
            if (
                cosine_similarity(entry.experience.embedding, experience.embedding)
                >= self._dedup_tau
            ):
                return existing_id
        return None

    def _evict_expired(self) -> None:
        """Evict entries that exceeded TTL."""
        now = self._clock()
        for experience_id, entry in list(self._entries.items()):
            ttl_deadline = entry.experience.ttl_deadline or (entry.inserted_at + self._ttl_seconds)
            if ttl_deadline <= now:
                del self._entries[experience_id]
                if self._persistence is not None:
                    self._persistence.delete_buffer_entries((experience_id,))
                self._audit_sink.emit(
                    "buffer.expired",
                    entry.experience.tenant_id,
                    {"experience_id": experience_id},
                )

    def _evict_over_capacity(self) -> None:
        """Evict the lowest-priority non-anchor entries until capacity is respected."""
        while len(self._entries) > self._max_items:
            candidates = [entry for entry in self._entries.values() if not entry.pinned_anchor]
            if not candidates:
                break
            victim = min(candidates, key=lambda entry: (entry.priority, entry.last_seen_at))
            del self._entries[victim.experience.id]
            if self._persistence is not None:
                self._persistence.delete_buffer_entries((victim.experience.id,))
            self._audit_sink.emit(
                "buffer.evicted",
                victim.experience.tenant_id,
                {"experience_id": victim.experience.id, "reason": "capacity"},
            )

    def _persist_entry(self, entry: _BufferEntry) -> None:
        """Persist a single buffer entry when a store is configured."""
        if self._persistence is None:
            return
        self._persistence.save_buffer_entry(
            {
                "experience": asdict(entry.experience),
                "priority": entry.priority,
                "inserted_at": entry.inserted_at,
                "last_seen_at": entry.last_seen_at,
                "novelty": entry.novelty,
                "pinned_anchor": entry.pinned_anchor,
                "dedup_group_id": entry.dedup_group_id,
            }
        )

    def _hydrate(self) -> None:
        """Load persisted entries into memory."""
        if self._persistence is None:
            return
        for payload in self._persistence.load_buffer_entries():
            experience = ExperienceRecord(**payload["experience"])
            self._entries[experience.id] = _BufferEntry(
                experience=experience,
                priority=float(payload["priority"]),
                inserted_at=float(payload["inserted_at"]),
                last_seen_at=float(payload["last_seen_at"]),
                novelty=float(payload["novelty"]),
                pinned_anchor=bool(payload["pinned_anchor"]),
                dedup_group_id=str(payload["dedup_group_id"]),
            )


class DriftTracker:
    """Sustained drift detector over projected embedding windows."""

    def __init__(
        self,
        thresholds: LearningThresholds,
        *,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._thresholds = thresholds
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._consecutive_breaches: dict[tuple[str, str], int] = defaultdict(int)

    def observe(
        self,
        *,
        tenant_id: str,
        domain: str,
        baseline_embeddings: Sequence[Sequence[float]],
        current_embeddings: Sequence[Sequence[float]],
    ) -> DriftSignal:
        """Evaluate sustained drift for a tenant/domain window."""
        reference_projection = centroid_distance_projection(baseline_embeddings)
        current_projection = centroid_distance_projection(current_embeddings)
        sample_size = int(min(reference_projection.size, current_projection.size))
        if sample_size == 0:
            return DriftSignal(
                psi=0.0,
                ks_statistic=0.0,
                ks_p_value=1.0,
                breached=False,
                consecutive_breaches=0,
                sample_size=0,
            )

        psi = population_stability_index(reference_projection, current_projection)
        ks_statistic, ks_p_value = ks_2samp(reference_projection, current_projection)
        breached = (
            psi > self._thresholds.drift_psi_threshold
            or ks_p_value < self._thresholds.drift_ks_p_threshold
        )
        key = (tenant_id.strip(), domain.strip())
        if breached:
            self._consecutive_breaches[key] += 1
        else:
            self._consecutive_breaches[key] = 0

        signal = DriftSignal(
            psi=psi,
            ks_statistic=ks_statistic,
            ks_p_value=ks_p_value,
            breached=breached,
            consecutive_breaches=self._consecutive_breaches[key],
            sample_size=sample_size,
        )
        self._audit_sink.emit(
            "drift.observed",
            tenant_id,
            {
                "domain": domain,
                "psi": psi,
                "ks_statistic": ks_statistic,
                "ks_p_value": ks_p_value,
                "breached": breached,
                "consecutive_breaches": signal.consecutive_breaches,
            },
        )
        return signal


class AdapterRegistry:
    """In-memory adapter registry with snapshot and rollback support."""

    def __init__(
        self,
        *,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], float] | None = None,
        persistence: AdapterPersistence | None = None,
    ) -> None:
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._clock = clock or time.time
        self._persistence = persistence
        self._active_by_scope: dict[tuple[str, str], str] = {}
        self._states: dict[str, AdapterState] = {}
        self._snapshots: dict[str, list[AdapterSnapshot]] = defaultdict(list)
        self._rollback_streaks: dict[tuple[str, str], int] = defaultdict(int)
        self._hydrate()

    def get_active_adapter(self, tenant_id: str, domain: str) -> str | None:
        """Return the active adapter identifier for a tenant/domain."""
        return self._active_by_scope.get((tenant_id.strip(), domain.strip()))

    def get_state(self, adapter_id: str) -> AdapterState | None:
        """Return the registry state for an adapter when present."""
        return self._states.get(adapter_id)

    def get_or_create_active_adapter(
        self,
        *,
        tenant_id: str,
        domain: str,
        base_model_id: str,
        rank_r: int,
    ) -> str:
        """Return the active adapter, creating one lazily when needed."""
        existing = self.get_active_adapter(tenant_id, domain)
        if existing is not None:
            return existing
        state = self.create_adapter(
            tenant_id=tenant_id,
            domain=domain,
            base_model_id=base_model_id,
            rank_r=rank_r,
        )
        self.set_active_adapter(tenant_id, domain, state.adapter_id)
        return state.adapter_id

    def create_adapter(
        self,
        *,
        tenant_id: str,
        domain: str,
        base_model_id: str,
        rank_r: int,
        parent_adapter_id: str | None = None,
        path_weights: str = "",
    ) -> AdapterState:
        """Create a new adapter state."""
        created_at = self._clock()
        adapter_id = f"lora:{tenant_id.strip()}:{domain.strip()}:{uuid.uuid4().hex[:12]}"
        state = AdapterState(
            adapter_id=adapter_id,
            tenant_id=tenant_id.strip(),
            domain=domain.strip(),
            base_model_id=base_model_id.strip(),
            rank_r=rank_r,
            created_at=created_at,
            parent_adapter_id=parent_adapter_id,
            path_weights=path_weights,
        )
        self._states[adapter_id] = state
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
        self._audit_sink.emit(
            "adapter.created",
            state.tenant_id,
            {
                "adapter_id": adapter_id,
                "domain": state.domain,
                "parent_adapter_id": parent_adapter_id,
            },
        )
        return state

    def set_active_adapter(self, tenant_id: str, domain: str, adapter_id: str) -> None:
        """Activate an adapter for the supplied tenant/domain scope."""
        state = self._states[adapter_id]
        scope = (tenant_id.strip(), domain.strip())
        state.last_used_at = self._clock()
        self._active_by_scope[scope] = adapter_id
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
            self._persistence.save_active_scope(tenant_id, domain, adapter_id)
        self._audit_sink.emit(
            "adapter.activated",
            state.tenant_id,
            {"adapter_id": adapter_id, "domain": state.domain},
        )

    def snapshot(
        self,
        *,
        adapter_id: str,
        reason: str,
        metrics: dict[str, float],
        pii_clean: bool = True,
        rollback_candidate: bool = True,
        path_weights: str = "",
        data_fingerprint: str = "",
    ) -> AdapterSnapshot:
        """Capture a rollback-capable adapter snapshot."""
        snapshot = AdapterSnapshot(
            snapshot_id=f"{adapter_id}:{int(self._clock() * 1000)}",
            adapter_id=adapter_id,
            created_at=self._clock(),
            metrics=dict(metrics),
            reason=reason,
            pii_clean=pii_clean,
            rollback_candidate=rollback_candidate,
            path_weights=path_weights,
            data_fingerprint=data_fingerprint,
        )
        self._snapshots[adapter_id].append(snapshot)
        if self._persistence is not None:
            state = self._states[adapter_id]
            payload = asdict(snapshot)
            payload["tenant_id"] = state.tenant_id
            payload["domain"] = state.domain
            self._persistence.save_adapter_snapshot(payload)
        self._audit_sink.emit(
            "adapter.snapshot",
            self._states[adapter_id].tenant_id,
            {"adapter_id": adapter_id, "snapshot_id": snapshot.snapshot_id, "reason": reason},
        )
        return snapshot

    def mark_metrics(
        self,
        adapter_id: str,
        metrics: dict[str, float],
        drift_stats: dict[str, float] | None = None,
    ) -> None:
        """Update runtime metrics tracked for an adapter."""
        state = self._states[adapter_id]
        state.metrics = dict(metrics)
        if drift_stats is not None:
            state.drift_stats = dict(drift_stats)
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))

    def update_artifact(
        self,
        adapter_id: str,
        *,
        path_weights: str = "",
        status: str | None = None,
    ) -> AdapterState:
        """Update the persisted artifact pointer and lifecycle status for an adapter."""
        state = self._states[adapter_id]
        if path_weights.strip():
            state.path_weights = path_weights.strip()
        if status is not None and status.strip():
            state.status = status.strip()
        state.last_used_at = self._clock()
        if self._persistence is not None:
            self._persistence.save_adapter_state(asdict(state))
        return state

    def rollback(self, adapter_id: str) -> AdapterSnapshot | None:
        """Rollback to the latest eligible snapshot."""
        state = self._states[adapter_id]
        for snapshot in reversed(self._snapshots.get(adapter_id, [])):
            if snapshot.rollback_candidate:
                state.rollback_to_snapshot_id = snapshot.snapshot_id
                state.status = "rolled_back"
                state.path_weights = snapshot.path_weights
                state.metrics = dict(snapshot.metrics)
                scope = (state.tenant_id, state.domain)
                if self._persistence is not None:
                    self._rollback_streaks[scope] = self._persistence.increment_rollback_streak(
                        state.tenant_id, state.domain
                    )
                    self._persistence.save_adapter_state(asdict(state))
                else:
                    self._rollback_streaks[scope] += 1
                self._audit_sink.emit(
                    "adapter.rollback",
                    state.tenant_id,
                    {"adapter_id": adapter_id, "snapshot_id": snapshot.snapshot_id},
                )
                return snapshot
        return None

    def rollback_streak(self, tenant_id: str, domain: str) -> int:
        """Return how many consecutive rollbacks happened for a scope."""
        return self._rollback_streaks[(tenant_id.strip(), domain.strip())]

    def reset_rollback_streak(self, tenant_id: str, domain: str) -> None:
        """Clear rollback streak tracking after a successful update."""
        scope = (tenant_id.strip(), domain.strip())
        self._rollback_streaks[scope] = 0
        if self._persistence is not None:
            self._persistence.reset_rollback_streak(scope[0], scope[1])

    def _hydrate(self) -> None:
        """Load persisted registry state."""
        if self._persistence is None:
            return
        for payload in self._persistence.load_adapter_states():
            state = AdapterState(**payload)
            self._states[state.adapter_id] = state
        for payload in self._persistence.load_adapter_snapshots():
            snapshot = AdapterSnapshot(
                snapshot_id=payload["snapshot_id"],
                adapter_id=payload["adapter_id"],
                created_at=float(payload["created_at"]),
                metrics=dict(payload.get("metrics", {})),
                reason=payload.get("reason", ""),
                pii_clean=bool(payload.get("pii_clean", True)),
                rollback_candidate=bool(payload.get("rollback_candidate", True)),
                path_weights=payload.get("path_weights", ""),
                data_fingerprint=payload.get("data_fingerprint", ""),
            )
            self._snapshots[snapshot.adapter_id].append(snapshot)
        self._active_by_scope.update(self._persistence.load_active_scopes())
        self._rollback_streaks.update(self._persistence.load_rollback_streaks())


class LifelongLearningSidecar:
    """Deterministic orchestration layer for continual adapter learning."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        tagger: Tagger | None = None,
        pii_sanitizer: PIISanitizer | None = None,
        prototype_store: PrototypeStore | None = None,
        semantic_store: SemanticMemoryStore | None = None,
        retrain_queue: RetrainQueue | None = None,
        registry: AdapterRegistry | None = None,
        buffer: PrioritizedEpisodicBuffer | None = None,
        lora_config: LoRAConfig | None = None,
        thresholds: LearningThresholds | None = None,
        drift_tracker: DriftTracker | None = None,
        audit_sink: AuditSink | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._clock = clock or time.time
        self._audit_sink = audit_sink or NoOpAuditSink()
        self._embedder = embedder
        self._tagger = tagger
        self._pii_sanitizer = pii_sanitizer or PIISanitizer()
        self._thresholds = thresholds or LearningThresholds()
        self._lora_config = lora_config or LoRAConfig()
        # Dependency injection must be explicit here. Components like
        # ``PrioritizedEpisodicBuffer`` implement ``__len__``, so using
        # truthiness would silently discard a valid but empty persistent buffer.
        self._prototype_store = (
            prototype_store if prototype_store is not None else InMemoryPrototypeStore()
        )
        self._semantic_store = (
            semantic_store if semantic_store is not None else InMemorySemanticMemoryStore()
        )
        self._retrain_queue = retrain_queue if retrain_queue is not None else ListRetrainQueue()
        self._registry = (
            registry
            if registry is not None
            else AdapterRegistry(
                audit_sink=self._audit_sink,
                clock=self._clock,
            )
        )
        self._buffer = (
            buffer
            if buffer is not None
            else PrioritizedEpisodicBuffer(
                max_items=self._thresholds.default_max_buffer_items,
                ttl_seconds=self._thresholds.default_ttl_seconds,
                dedup_tau=self._thresholds.dedup_tau,
                audit_sink=self._audit_sink,
                clock=self._clock,
            )
        )
        self._drift_tracker = (
            drift_tracker
            if drift_tracker is not None
            else DriftTracker(
                self._thresholds,
                audit_sink=self._audit_sink,
            )
        )

    @property
    def buffer(self) -> PrioritizedEpisodicBuffer:
        """Expose the replay buffer for observability and tests."""
        return self._buffer

    @property
    def registry(self) -> AdapterRegistry:
        """Expose the adapter registry for observability and tests."""
        return self._registry

    def on_interaction(
        self,
        *,
        tenant_id: str,
        user_id: str,
        text: str,
        trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ExperienceRecord:
        """Sanitize, tag, embed, and enqueue an interaction for replay."""
        tenant_key = tenant_id.strip()
        sanitized = self._pii_sanitizer.sanitize(text, tenant_id=tenant_key)
        tag: dict[str, Any] = {}
        if self._tagger is not None:
            tag.update(self._tagger.tag(sanitized.sanitized))
        # Explicit per-event metadata must win over inferred defaults.
        tag.update(metadata or {})

        domain = str(tag.get("domain", "general")).strip() or "general"
        intent = str(tag.get("intent", "unknown")).strip() or "unknown"
        confidence = float(tag.get("confidence", 0.5))
        novelty = float(tag.get("novelty", 1.0))
        cost_of_error_raw = tag.get("cost_of_error")
        cost_of_error = float(cost_of_error_raw) if cost_of_error_raw is not None else None
        ttl_deadline = float(
            tag.get("ttl_deadline", self._clock() + self._thresholds.default_ttl_seconds)
        )

        embedding = tuple(float(value) for value in self._embedder.embed(sanitized.sanitized))
        priority = compute_priority(confidence, novelty, cost_of_error)
        semantic_hash = str(tag.get("semantic_hash", stable_text_hash(sanitized.sanitized)))

        experience = ExperienceRecord(
            id=f"exp:{uuid.uuid4().hex}",
            tenant_id=tenant_key,
            user_id=user_id,
            ts=self._clock(),
            domain=domain,
            intent=intent,
            text=sanitized.sanitized,
            confidence=confidence,
            priority=priority,
            cost_of_error=cost_of_error,
            embedding=embedding,
            semantic_hash=semantic_hash,
            ttl_deadline=ttl_deadline,
            trace_id=trace_id,
            pii_categories=tuple(category.value for category in sanitized.pii_categories),
            metadata={
                **tag,
                "pii_fragment_keys": sorted(sanitized.encrypted_fragments.keys()),
            },
        )
        pinned_anchor = bool(tag.get("pinned_anchor", confidence >= 0.9))
        self._buffer.add(experience, novelty=novelty, pinned_anchor=pinned_anchor)
        self._audit_sink.emit(
            "interaction.ingested",
            tenant_key,
            {
                "experience_id": experience.id,
                "domain": experience.domain,
                "trace_id": trace_id,
                "priority": experience.priority,
            },
        )
        return experience

    def make_mixed_batch(self, *, tenant_id: str, domain: str) -> MixedBatch:
        """Build the K1/K2/K3 rehearsal batch for a domain."""
        new_examples = self._buffer.sample(
            tenant_id=tenant_id,
            domain=domain,
            k=self._lora_config.new_examples,
            high_priority=True,
        )
        anchor_examples = self._buffer.sample(
            tenant_id=tenant_id,
            domain=None,
            k=self._lora_config.anchor_examples,
            anchors_only=True,
            high_priority=True,
        )
        prototype_examples = tuple(
            self._prototype_store.sample(
                tenant_id=tenant_id,
                domain=domain,
                k=self._lora_config.prototype_examples,
            )
        )
        return MixedBatch(
            new_examples=tuple(new_examples),
            anchor_examples=tuple(anchor_examples),
            prototype_examples=prototype_examples,
        )

    def plan_micro_update(
        self,
        *,
        tenant_id: str,
        domain: str,
        policy_violation: bool = False,
    ) -> MicroUpdatePlan:
        """Plan a conservative adapter micro-update without touching model weights."""
        batch = self.make_mixed_batch(tenant_id=tenant_id, domain=domain)
        if batch.size == 0:
            raise ValueError("cannot plan a micro-update without examples")

        adapter_id = self._registry.get_or_create_active_adapter(
            tenant_id=tenant_id,
            domain=domain,
            base_model_id=self._lora_config.base_model_id,
            rank_r=self._lora_config.rank_r,
        )
        new_examples = batch.new_examples or batch.anchor_examples or batch.prototype_examples
        avg_confidence = float(
            sum(example.confidence for example in new_examples) / len(new_examples)
        )
        max_cost = max(
            (example.cost_of_error or 0.0 for example in new_examples),
            default=0.0,
        )
        learning_rate, current_risk = schedule_learning_rate(
            self._lora_config.base_learning_rate,
            avg_confidence,
            max_cost,
            policy_violation=policy_violation,
            min_scale=self._lora_config.min_learning_rate_scale,
            max_scale=self._lora_config.max_learning_rate_scale,
        )
        plan = MicroUpdatePlan(
            tenant_id=tenant_id,
            domain=domain,
            adapter_id=adapter_id,
            learning_rate=learning_rate,
            risk_score=current_risk,
            batch=batch,
        )
        self._audit_sink.emit(
            "micro_update.planned",
            tenant_id,
            {
                "adapter_id": adapter_id,
                "domain": domain,
                "learning_rate": learning_rate,
                "risk_score": current_risk,
                "batch_size": batch.size,
            },
        )
        return plan

    def evaluate_update(
        self,
        *,
        before_scores: dict[str, float],
        after_scores: dict[str, float],
        critical_domains: Iterable[str] = (),
    ) -> EvaluationSummary:
        """Apply rollback guardrails to per-domain regression metrics."""
        critical = set(critical_domains)
        delta_by_domain: dict[str, float] = {}
        rollback_required = False
        reasons: list[str] = []

        for domain in sorted(set(before_scores).intersection(after_scores)):
            delta = after_scores[domain] - before_scores[domain]
            delta_by_domain[domain] = delta
            threshold = (
                self._thresholds.critical_rollback_pct
                if domain in critical
                else self._thresholds.non_critical_rollback_pct
            )
            if (
                before_scores[domain] > 0.0
                and ((before_scores[domain] - after_scores[domain]) / before_scores[domain])
                > threshold
            ):
                rollback_required = True
                reasons.append(f"{domain} regressed beyond {threshold:.0%}")

        cfs = compute_cfs(before_scores, after_scores)
        suspend_learning = cfs > self._thresholds.cfs_suspend_threshold
        if suspend_learning:
            reasons.append(f"CFS {cfs:.3f} exceeded {self._thresholds.cfs_suspend_threshold:.3f}")

        return EvaluationSummary(
            before_scores=dict(before_scores),
            after_scores=dict(after_scores),
            delta_by_domain=delta_by_domain,
            cfs=cfs,
            rollback_required=rollback_required,
            suspend_learning=suspend_learning,
            reason="; ".join(reasons),
        )

    def manage_adapters(
        self,
        *,
        tenant_id: str,
        domain: str,
        baseline_embeddings: Sequence[Sequence[float]],
        current_embeddings: Sequence[Sequence[float]],
        metrics: dict[str, float],
        merge_backend: MergeBackend | None = None,
    ) -> AdapterDecision:
        """Create, fuse, or leave adapters unchanged based on sustained drift."""
        active_adapter = self._registry.get_or_create_active_adapter(
            tenant_id=tenant_id,
            domain=domain,
            base_model_id=self._lora_config.base_model_id,
            rank_r=self._lora_config.rank_r,
        )
        signal = self._drift_tracker.observe(
            tenant_id=tenant_id,
            domain=domain,
            baseline_embeddings=baseline_embeddings,
            current_embeddings=current_embeddings,
        )
        self._registry.mark_metrics(
            active_adapter,
            metrics,
            drift_stats={
                "psi": signal.psi,
                "ks_statistic": signal.ks_statistic,
                "ks_p_value": signal.ks_p_value,
            },
        )

        if signal.breached and signal.consecutive_breaches >= self._thresholds.sustained_windows:
            child = self._registry.create_adapter(
                tenant_id=tenant_id,
                domain=domain,
                base_model_id=self._lora_config.base_model_id,
                rank_r=self._lora_config.rank_r,
                parent_adapter_id=active_adapter,
            )
            self._registry.set_active_adapter(tenant_id, domain, child.adapter_id)
            self._registry.snapshot(
                adapter_id=child.adapter_id,
                reason="create_child_on_drift",
                metrics=metrics,
            )
            return AdapterDecision(
                action=AdapterLifecycleAction.CREATE_CHILD,
                adapter_id=child.adapter_id,
                reason="sustained drift breached thresholds",
                drift_signal=signal,
                metrics=dict(metrics),
            )

        if merge_backend is not None and metrics.get("should_fuse", 0.0) >= 1.0:
            merged_id = merge_backend.merge_into(
                adapter_name=f"{tenant_id}:{domain}:merged",
                method="ties",
                density=0.2,
            )
            merged = self._registry.create_adapter(
                tenant_id=tenant_id,
                domain=domain,
                base_model_id=self._lora_config.base_model_id,
                rank_r=self._lora_config.rank_r,
                parent_adapter_id=active_adapter,
                path_weights=merged_id,
            )
            self._registry.set_active_adapter(tenant_id, domain, merged.adapter_id)
            self._registry.snapshot(
                adapter_id=merged.adapter_id,
                reason="fuse_adapters",
                metrics=metrics,
                path_weights=merged_id,
            )
            return AdapterDecision(
                action=AdapterLifecycleAction.FUSE,
                adapter_id=merged.adapter_id,
                reason="merge backend promoted a fused adapter",
                drift_signal=signal,
                metrics=dict(metrics),
            )

        return AdapterDecision(
            action=AdapterLifecycleAction.NOOP,
            adapter_id=active_adapter,
            reason="no sustained drift or fusion trigger detected",
            drift_signal=signal,
            metrics=dict(metrics),
        )

    def maybe_rollback(
        self,
        *,
        tenant_id: str,
        domain: str,
        evaluation: EvaluationSummary,
    ) -> AdapterDecision:
        """Rollback the active adapter when the evaluation gate fails."""
        adapter_id = self._registry.get_active_adapter(tenant_id, domain)
        if adapter_id is None:
            return AdapterDecision(
                action=AdapterLifecycleAction.NOOP,
                adapter_id=None,
                reason="no active adapter to rollback",
            )
        if not evaluation.rollback_required and not evaluation.suspend_learning:
            return AdapterDecision(
                action=AdapterLifecycleAction.NOOP,
                adapter_id=adapter_id,
                reason="evaluation gate passed",
            )

        snapshot = self._registry.rollback(adapter_id)
        if snapshot is None:
            return AdapterDecision(
                action=AdapterLifecycleAction.NOOP,
                adapter_id=adapter_id,
                reason="evaluation failed but no rollback snapshot exists",
            )

        return AdapterDecision(
            action=AdapterLifecycleAction.ROLLBACK,
            adapter_id=adapter_id,
            reason=evaluation.reason or "evaluation gate requested rollback",
            metrics=snapshot.metrics,
        )

    def execute_micro_update(
        self,
        *,
        tenant_id: str,
        domain: str,
        backend: MicroUpdateBackend,
        policy_violation: bool = False,
        critical_domains: Iterable[str] = (),
        merge_backend: MergeBackend | None = None,
    ) -> MicroUpdateExecution:
        """Plan, execute, evaluate, and either commit or rollback a micro-update."""
        plan = self.plan_micro_update(
            tenant_id=tenant_id,
            domain=domain,
            policy_violation=policy_violation,
        )
        state = self._registry.get_state(plan.adapter_id)
        current_metrics = dict(state.metrics) if state is not None else {}
        current_path_weights = state.path_weights if state is not None else ""
        self._registry.snapshot(
            adapter_id=plan.adapter_id,
            reason="pre_micro_update",
            metrics=current_metrics,
            path_weights=current_path_weights,
        )

        backend_result = backend.execute(plan)
        if backend_result.adapter_id != plan.adapter_id:
            raise ValueError(
                "micro-update backend returned a different adapter_id than the planned adapter"
            )

        self._registry.update_artifact(
            plan.adapter_id,
            path_weights=backend_result.artifact_path,
            status="trained",
        )
        applied_metrics = (
            dict(backend_result.training_metrics)
            if backend_result.training_metrics
            else dict(backend_result.after_scores)
        )
        self._registry.mark_metrics(plan.adapter_id, applied_metrics)

        evaluation = self.evaluate_update(
            before_scores=backend_result.before_scores,
            after_scores=backend_result.after_scores,
            critical_domains=critical_domains,
        )
        rollback_decision = self.maybe_rollback(
            tenant_id=tenant_id,
            domain=domain,
            evaluation=evaluation,
        )

        lifecycle_decision = AdapterDecision(
            action=AdapterLifecycleAction.NOOP,
            adapter_id=plan.adapter_id,
            reason="lifecycle management skipped",
        )
        committed = rollback_decision.action is not AdapterLifecycleAction.ROLLBACK
        if committed:
            self._registry.reset_rollback_streak(tenant_id, domain)
            self._registry.snapshot(
                adapter_id=plan.adapter_id,
                reason=backend_result.snapshot_reason,
                metrics=dict(backend_result.after_scores),
                path_weights=backend_result.artifact_path,
                data_fingerprint=backend_result.data_fingerprint,
            )
            if backend_result.baseline_embeddings and backend_result.current_embeddings:
                lifecycle_decision = self.manage_adapters(
                    tenant_id=tenant_id,
                    domain=domain,
                    baseline_embeddings=backend_result.baseline_embeddings,
                    current_embeddings=backend_result.current_embeddings,
                    metrics=applied_metrics,
                    merge_backend=merge_backend,
                )
            else:
                lifecycle_decision = AdapterDecision(
                    action=AdapterLifecycleAction.NOOP,
                    adapter_id=plan.adapter_id,
                    reason="backend returned no drift windows for lifecycle management",
                    metrics=applied_metrics,
                )
        else:
            lifecycle_decision = AdapterDecision(
                action=AdapterLifecycleAction.NOOP,
                adapter_id=plan.adapter_id,
                reason="execution rolled back before lifecycle management",
                metrics=applied_metrics,
            )

        self._audit_sink.emit(
            "micro_update.executed",
            tenant_id,
            {
                "adapter_id": plan.adapter_id,
                "domain": domain,
                "backend_name": backend_result.backend_name,
                "committed": committed,
                "rollback_action": rollback_decision.action.value,
                "lifecycle_action": lifecycle_decision.action.value,
                "cfs": evaluation.cfs,
            },
        )
        return MicroUpdateExecution(
            plan=plan,
            backend_result=backend_result,
            evaluation=evaluation,
            rollback_decision=rollback_decision,
            lifecycle_decision=lifecycle_decision,
            committed=committed,
        )

    def should_suspend_learning(self, *, tenant_id: str, domain: str) -> bool:
        """Return whether a scope exceeded the rollback streak limit."""
        return (
            self._registry.rollback_streak(tenant_id, domain)
            >= self._thresholds.rollback_streak_limit
        )

    def status(self, *, tenant_id: str, domain: str | None = None) -> dict[str, Any]:
        """Return deterministic observability data for a tenant-scoped sidecar view."""
        tenant_key = tenant_id.strip()
        if not tenant_key:
            raise ValueError("tenant_id must be non-blank")

        domain_key: str | None = None
        if domain is not None:
            domain_key = domain.strip()
            if not domain_key:
                raise ValueError("domain must be non-blank when provided")

        self._buffer._evict_expired()  # noqa: SLF001
        scoped_entries = [
            entry
            for entry in self._buffer._entries.values()  # noqa: SLF001
            if entry.experience.tenant_id == tenant_key
            and (domain_key is None or entry.experience.domain == domain_key)
        ]
        known_domains = sorted({entry.experience.domain for entry in scoped_entries})
        active_scopes = [
            {"domain": current_domain, "adapter_id": adapter_id}
            for (scope_tenant, current_domain), adapter_id in sorted(  # noqa: C416
                self._registry._active_by_scope.items()  # noqa: SLF001
            )
            if scope_tenant == tenant_key and (domain_key is None or current_domain == domain_key)
        ]
        adapter_count = sum(
            1
            for state in self._registry._states.values()  # noqa: SLF001
            if state.tenant_id == tenant_key and (domain_key is None or state.domain == domain_key)
        )

        active_adapter_id = None
        rollback_streak = 0
        snapshot_count = 0
        if domain_key is not None:
            active_adapter_id = self._registry.get_active_adapter(tenant_key, domain_key)
            rollback_streak = self._registry.rollback_streak(tenant_key, domain_key)
            if active_adapter_id is not None:
                snapshot_count = len(self._registry._snapshots.get(active_adapter_id, ()))  # noqa: SLF001

        return {
            "enabled": True,
            "tenant_id": tenant_key,
            "domain": domain_key,
            "persisted": (
                self._buffer._persistence is not None and self._registry._persistence is not None  # noqa: SLF001
            ),
            "buffer_items": len(scoped_entries),
            "known_domains": known_domains,
            "active_scopes": active_scopes,
            "adapter_count": adapter_count,
            "active_adapter_id": active_adapter_id,
            "snapshot_count": snapshot_count,
            "rollback_streak": rollback_streak,
            "suspend_learning": (
                self.should_suspend_learning(tenant_id=tenant_key, domain=domain_key)
                if domain_key is not None
                else False
            ),
            "buffer_capacity": self._thresholds.default_max_buffer_items,
            "ttl_seconds": self._thresholds.default_ttl_seconds,
        }

    def forget(self, *, tenant_id: str, user_id: str, query: str) -> dict[str, Any]:
        """Delete non-parametric traces and queue replay from a clean snapshot."""
        deleted_exp_ids = self._buffer.delete_by_query(tenant_id=tenant_id, query=query)
        deleted_chunk_ids = self._semantic_store.delete_by_query(tenant_id=tenant_id, query=query)
        deleted_prototypes = self._prototype_store.purge_by_source_ids(deleted_exp_ids)

        replay_job = {
            "type": "retrain_from_clean_snapshot",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "query": query,
            "deleted_experience_ids": deleted_exp_ids,
        }
        self._retrain_queue.put(replay_job)
        self._audit_sink.emit(
            "forget.completed",
            tenant_id,
            {
                "user_id": user_id,
                "query": query,
                "deleted_experience_ids": deleted_exp_ids,
                "deleted_chunk_ids": deleted_chunk_ids,
                "deleted_prototypes": deleted_prototypes,
            },
        )
        return {
            "deleted_exp_ids": deleted_exp_ids,
            "deleted_chunk_ids": deleted_chunk_ids,
            "deleted_prototypes": deleted_prototypes,
            "retrain_job": replay_job,
        }
