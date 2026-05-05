# Crypto-Shredding Executable Evidence

Status: implemented evidence for issue `#285`.

## What the repository demonstrates now

- A fact can be marked as erased in `shredded_keys`.
- Mutable payload surfaces in `facts` are replaced with a non-PII tombstone.
- Mutable retrieval/index surfaces are purged for the erased fact:
  - `facts_fts`
  - `fact_embeddings`
  - pending `enrichment_jobs`
- Ledger continuity remains valid because `ledger_events` is not mutated by the erasure path.
- Subject-scoped erasure can be executed through `shred_by_source(...)`.

## What the repository does not claim yet

- Per-fact envelope-key destruction proven independently of payload-surface redaction.
- Backup/media destruction outside the live SQLite surfaces touched by this module.
- External anchor or third-party cache erasure.

## Evidence tests

- `tests/test_crypto_shredding_end_to_end.py`
- `tests/test_crypto_shredder.py`

## Residual limitation

The current codebase proves executable unreadability of mutable fact surfaces and
search indexes. It does not, by itself, prove a fully separated per-fact key
hierarchy across every encrypted field in the repository.
