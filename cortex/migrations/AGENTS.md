# AGENTS.md - cortex/migrations

Root `AGENTS.md` applies first. These rules add migration-specific constraints.

## Risk Posture

Schema changes can corrupt tenant data, break ledger verification, or make old
databases unrecoverable. This repo's active migration contract is implemented in
`cortex/migrations/core.py` and `cortex/migrations/registry.py`; do not document
or require Alembic unless the repo actually adds Alembic as an active mechanism.

Before editing migrations:

- Read `cortex/migrations/core.py` and `cortex/migrations/registry.py`.
- Identify affected tables, indexes, virtual tables, and tenant columns.
- Document rollback or downgrade behavior in the migration or PR notes.
- Confirm failed migrations do not advance `schema_version`.

## Migration Inventory

- `001_ledger_events.sql`: ledger event foundation.
- `002_enrichment_jobs.sql`: enrichment queue.
- `016_crypto_shredding.sql`: encryption/key lifecycle support.
- `017_hlc_crdt.sql`: HLC and CRDT support.
- `mig_ledger.py`: ledger-related schema.
- `mig_tenant.py`: tenant isolation schema.
- `mig_consensus.py`: consensus/vote-ledger schema.
- `mig_cognitive_layer.py`: vector/cognitive schema, including sqlite-vec risk.
- `mig_fts.py`: full-text-search schema.
- `mig_tombstone.py`: deletion/tombstone behavior.

## Migration Rules

- Do not mutate historical migration files unless the change is explicitly a
  compatibility fix and is documented as such.
- Do not drop or rewrite tenant-scoped data without a preservation or backfill
  strategy.
- Do not change ledger tables without hash-chain compatibility tests.
- Do not change sqlite-vec/FTS behavior without graceful-degradation coverage.
- Do not store plaintext secrets or sensitive tenant payloads in new columns.
- Do not advance schema version after a failed migration.

## Focused Checks

```bash
pytest tests/test_migrations_core.py \
       tests/test_ledger_schema_compat.py \
       tests/test_ledger_integrity_verification.py \
       tests/test_ledger_checkpointing.py \
       tests/test_ledger_tenant_hash_binding.py -v
```

For sqlite-vec or L2 memory schema changes, also run the relevant memory/vector
tests from `cortex/memory/AGENTS.md`.
