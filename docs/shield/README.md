# Shield

Scope: runtime hardening (origin authenticity, replay/freshness, immutable ledger privacy, crypto-shredding, tenant isolation).

- M4: strict origin signatures + permissions registry
- M5: atomic replay/freshness admission (event-id/nonce + idempotency)
- M6: no-PII immutable ledger policy (allowlists + scrubbing)
- M7: subject/fact scoped crypto-shredding proof (derivative purge + tombstone continuity)
- PR-272: tenant isolation / admin bootstrap hardening
