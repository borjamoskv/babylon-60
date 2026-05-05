# AGENTS.md - cortex/engine

Root `AGENTS.md` applies first. These rules add engine-specific constraints.

## Risk Posture

`cortex/engine/` is a critical surface. Small changes can alter guard admission,
tenant scoping, ledger continuity, persistence transactions, or irreversible
state transitions.

Before editing engine code:

- Identify whether the change affects reads, writes, guards, ledger emission,
  snapshots, deletion, trust scoring, or background execution.
- Read the tests that cover the changed behavior before patching.
- Treat generated output as conjecture until it crosses deterministic guards.

## Critical Modules

- `fact_store_core.py`: canonical fact persistence boundary.
- `guard_pipeline.py`, `guard_adapters.py`, `storage_guard.py`: admission and
  fail-closed behavior.
- `transaction_mixin.py`: ledger and persistence transaction coupling.
- `crystallizer.py`: permanent fact synthesis and persistence.
- `reaper.py`: destructive or tombstone-oriented paths.
- `snapshots.py`: rollback and recovery support where implemented.
- `semantic_hash.py`: content hash semantics.
- `consensus.py`: multi-agent quorum and vote-ledger interaction.
- `mutation_engine.py`: state mutation and verification surfaces.
- `trust_registry.py`: identity and trust metadata propagation.
- `bridge_guard.py`: admission guard for bridge-style writes.

## Engine Rules

- Do not write facts without guard admission and tenant validation.
- Do not bypass `fact_store_core.py` for persistent fact writes.
- Do not add permissive fallbacks around guard failures.
- Do not perform irreversible deletion without tenant scope and audit rationale.
- Do not change hash semantics without ledger/hash regression tests.
- Do not change quorum or vote-ledger behavior without consensus tests.
- Do not add blocking calls in async engine paths.
- Do not hide deterministic failures behind broad exception handling.

## Focused Checks

Use the narrowest relevant command first, then broaden if shared behavior moved.

```bash
pytest tests/test_guard_pipeline.py \
       tests/test_daemon_guarded_persistence.py \
       tests/test_store_mixin.py \
       tests/test_store_request_taint.py -v

pytest tests/ -k "engine or store or crystal or reaper or consensus" -v
```

For ledger-sensitive engine changes, also run the focused ledger checks listed in
the root `AGENTS.md`.
