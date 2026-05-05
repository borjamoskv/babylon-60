# Replay And Freshness Strict Mode

Status: draft

M5 adds replay and freshness protection for signed ledger-origin events. It
builds on M4 origin signatures and does not replace signature validation.

## Runtime Contract

`LedgerWriter` can be configured with `ReplayProtectionPolicy`. When enabled,
the writer:

- requires an M4 `OriginSignaturePolicy`;
- checks `origin.signed_at` against a freshness window before persistence;
- opens a SQLite `BEGIN IMMEDIATE` transaction for the protected write;
- detects idempotent retries before computing a new chain hash;
- reserves the origin nonce and event id in `ledger_origin_replay`;
- inserts the ledger event in the same transaction;
- enqueues enrichment only after the transaction commits.

If replay reservation succeeds but the ledger insert fails, the transaction
rolls back and the nonce reservation is removed with it.

## Replay Table

`ledger_origin_replay` is a sidecar table. It does not mutate existing
`ledger_events` rows and does not alter historical hash-chain payloads.

Constraints:

- `UNIQUE(tenant_id, actor_id, key_id, nonce)`
- `UNIQUE(tenant_id, event_id)`

The table stores:

- tenant id;
- actor id;
- key id;
- nonce;
- event id;
- signed timestamp;
- origin signature;
- committed event hash.

## Idempotent Retry

Retrying the same signed event with the same tenant, event id, nonce, and
origin signature returns the existing event id. It does not insert another
ledger row and does not enqueue another enrichment job.

Reusing a nonce for a different event is rejected. Reusing an event id with a
different signed origin is rejected.

## Freshness

Default policy:

- max age: 300 seconds;
- max future clock skew: 60 seconds.

Events older than the max age are rejected as stale. Events signed too far in
the future are rejected as clock-skew/tampering candidates.

## Migration

Migration 23 creates `ledger_origin_replay`.

Downgrade target: 22.

Rollback strategy:

```sql
DROP TABLE ledger_origin_replay;
```

Rollback disables replay protection but does not rewrite `ledger_events`, fact
tables, vector tables, or hash-chain data.

## Current Limitations

M5 does not persist a durable key registry, does not perform TPM/HSM key
attestation, and does not prove global completeness across independent
databases. It provides per-database replay/freshness enforcement for protected
ledger writes.
