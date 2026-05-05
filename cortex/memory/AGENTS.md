# AGENTS.md - cortex/memory

Root `AGENTS.md` applies first. These rules add memory-specific constraints.

## Risk Posture

`cortex/memory/` is a critical surface because it combines public memory APIs,
tenant isolation, fact aging, vector retrieval, L2/L3 storage, provenance, and
local memory-ledger continuity.

Before editing memory code:

- Identify every persistent read/write path touched by the change.
- Verify explicit `tenant_id` propagation.
- Check whether taint, provenance, encryption, or memory-ledger continuity is
  affected.
- Read focused tests before patching.

## Critical Modules

- `ledger.py`: L3 memory hash-chain continuity.
- `guardrails.py`, `thalamus.py`, `manager.py`: memory admission boundaries.
- `sqlite_vec_store.py`, `l2_hybrid_search.py`: L2 vector persistence and FTS.
- `episodic.py`, `frequency.py`, `drift.py`: fact aging and temporal behavior.
- `consolidation.py`, `reconsolidation.py`, `dream.py`: consolidation paths.
- `crdt.py`: commutativity and idempotency requirements.
- `pii_sanitizer.py`: sensitive-content handling.
- `schemas.py`, `models.py`: public data contracts.

## Memory Rules

- Persistent reads and writes must accept or resolve an explicit `tenant_id`.
- SQL queries over tenant data must filter by tenant before returning facts.
- Do not strip taint or provenance metadata when the response contract can carry
  it.
- Do not store sensitive content or metadata in plaintext unless the route is
  explicitly documented as plaintext opt-in.
- Aging, consolidation, and deletion paths must be tenant-scoped and auditable.
- CRDT changes must preserve commutativity, convergence, and idempotency.
- Vector/ML code may use floats; persisted trust thresholds and tenant decisions
  must not depend on unreviewed float semantics.

## Focused Checks

```bash
pytest tests/test_ledger_l3.py \
       tests/test_memory_admission_tenant.py \
       tests/test_memory_manager.py \
       tests/test_memory_l2_migration_cli.py \
       tests/test_taint_preserves_encryption.py -v

pytest tests/ -k "memory or tenant or ledger or taint or crdt" -v
```

For L2 encryption or FTS changes, include `tests/test_search_exergy.py` when it
exists in the changed branch.
