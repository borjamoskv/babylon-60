# Continual Learning Sidecar

`cortex/extensions/continual_learning` implements the minimum viable control plane for frozen-base continual learning in CORTEX 6.

It is intentionally separated from the core write-path:

- the base model remains frozen
- online learning happens through adapter plans, not direct weight mutation
- replay, drift, rollback, and forgetting decisions stay deterministic and testable

## Included in the MVP

- prioritized episodic buffer with TTL and semantic deduplication
- mixed rehearsal batches using `K1/K2/K3 = 8/16/8`
- conservative learning-rate scheduling tied to confidence and cost of error
- A-GEM gradient projection helper
- drift gating with PSI and KS over embedding projections
- adapter registry with snapshot and rollback support
- SQLite-backed persistence for replay buffer, prototypes, semantic chunks, adapters, snapshots, and replay jobs
- selective forgetting for non-parametric memory plus replay queueing
- optional wiring into `CortexMemoryManager` through `CORTEX_CONTINUAL_LEARNING=1`

## Not included yet

- PEFT / Torch execution inside the core repo
- promotion pipelines into production inference runtimes

## Integration contract

Wire the sidecar at the edge of interaction ingestion:

1. sanitize and tag the interaction
2. embed and insert it into the replay buffer
3. periodically call `plan_micro_update()` for the active tenant/domain
4. run the real LoRA backend outside the core repo boundary
5. feed metrics into `evaluate_update()` and `manage_adapters()`
6. call `forget()` when selective deletion or privacy replay is required

This keeps continual learning aligned with CORTEX trust constraints while leaving heavy training infrastructure pluggable.

## Persistence and Activation

The sidecar now supports a dedicated SQLite state store via
`SQLiteContinualLearningStore`. When enabled from the runtime memory layer,
`MemoryMixin` wires persistent implementations for:

- replay buffer state
- prototype examples
- semantic memory chunks
- adapter registry and snapshots
- clean replay jobs after selective forgetting

Runtime activation is opt-in:

- `CORTEX_CONTINUAL_LEARNING=1` enables the sidecar in `MemoryMixin`
- `CORTEX_CONTINUAL_LEARNING_DB_PATH=/abs/path/continual_learning.db` overrides the default store location
- `CORTEX_CONTINUAL_LEARNING_BACKEND=mlx` enables automatic execution backend wiring
- `CORTEX_CONTINUAL_LEARNING_BASE_MODEL=<mlx-model-id>` selects the frozen base model
- `CORTEX_CONTINUAL_LEARNING_SCORE_COMMAND="<executable> <args...>"` is mandatory for commit-time scoring
- `CORTEX_CONTINUAL_LEARNING_WORK_DIR=/abs/path/runs` overrides the training workspace
- `CORTEX_CONTINUAL_LEARNING_DRY_RUN=1` keeps MLX execution in dataset-only mode for safe smoke tests

The activation path fails closed. If the embedder is async-only or the store
cannot be initialized, the main memory pipeline stays operational and the
sidecar is skipped with a warning. The execution backend is also fail-closed:
if `CORTEX_CONTINUAL_LEARNING_BACKEND` is set but the scorer or model
configuration is incomplete, `MemoryMixin` keeps the control-plane sidecar
enabled and leaves execution disabled.

## Public Control Surface

The legacy memories API now exposes a safe control-plane surface for the sidecar:

- `GET /v1/memories/continual/status`
- `POST /v1/memories/continual/plan`
- `POST /v1/memories/continual/execute`
- `POST /v1/memories/continual/forget`

These endpoints stay tenant-scoped through the existing auth layer and only
interact with deterministic sidecar functions. They do not execute LoRA weight
updates inside the core repo unless an external backend has been explicitly
injected; by default they expose observability, planning, and selective
forgetting controls.

## External Training Backend

The sidecar now defines a `MicroUpdateBackend` contract plus a concrete
`MLXLoRABackend` implementation for Apple Silicon / MLX flows.

Execution model:

1. `plan_micro_update()` builds the deterministic batch and risk settings
2. the external backend materializes a dataset and trains outside the core loop
3. the backend returns `before_scores` / `after_scores` plus artifact metadata
4. the sidecar evaluates rollback gates, snapshots, and optional drift actions

The scoring contract is mandatory. A backend must return explicit
`before_scores` and `after_scores`; otherwise the sidecar refuses to treat the
update as committed. This keeps write-path promotion deterministic even when the
trainer itself is external.

### Subprocess scorer contract

`SubprocessScoreProvider` is the default runtime bridge used by
`build_backend_from_env()`.

Input arrives on `stdin` as JSON:

```json
{
  "artifact_path": "/abs/path/to/adapter",
  "plan": {
    "tenant_id": "tenant-a",
    "domain": "support",
    "adapter_id": "lora:tenant-a:support:default",
    "learning_rate": 0.00005,
    "risk_score": 0.2,
    "batch": {
      "new_examples": [],
      "anchor_examples": [],
      "prototype_examples": []
    }
  }
}
```

The scorer must emit JSON on `stdout` with at least:

```json
{
  "before_scores": { "support": 0.81 },
  "after_scores": { "support": 0.84 }
}
```

Any non-zero exit code, invalid JSON, or missing score maps leaves the trainer
disabled or the execution aborted. No permissive fallback is applied.
