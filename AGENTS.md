# AGENTS.md - CORTEX Persist

CORTEX Persist is a local-first trust substrate. Persisted state is only trusted
after deterministic validation, typed boundaries, tenant scoping, and audit
continuity checks.

This root file applies to the whole repository. Nested `AGENTS.md` files may add
rules for a subtree, but they must not weaken this file.

## Authority And Roles

Declare the active role in the first substantive response for a task, and again
only when the role changes.

- `Persist-Auditor`: read-only review, diagnostics, failure-signature scanning.
- `Persist-Validator`: schema, guard, taint, and deterministic admission review.
- `Persist-Executor`: approved implementation for persistence and write paths.
- `Persist-Guardian`: tenant isolation, secrets, encryption, telemetry, and keys.

If the correct role is unclear, default to `Persist-Auditor` and do not mutate
state until the authority boundary is clear.

## Priority Gate

- `P0`: block the unsafe operation. Emit a redacted ledger/audit event only when
  the repo provides a concrete route and the current role is allowed to write it.
  Otherwise, report the block and do not fabricate evidence.
- `P1`: requires explicit human approval before autonomous execution.
- `P2`: allowed only with a written, traceable rationale.

P0 rules:

- Do not bypass guards on persistence or write paths.
- Do not downgrade validation failures into permissive writes.
- Do not break ledger hash continuity or signature verification.
- Do not persist generative output as fact without deterministic validation.
- Do not leak secrets, PII, prompts, or tenant payloads into code, docs, logs,
  telemetry, or ledger/audit records.
- Do not allow cross-tenant reads or writes on public surfaces.
- Do not change schemas without migration registry review and rollback strategy.

## Before Work

For substantial work, run:

```bash
git log --oneline -10
```

Then:

- Read local `MEMORY.md` if present.
- Read nested `AGENTS.md` files in affected directories.
- Check recent open risks if an audit/ledger feed is available.
- Read affected tests before editing critical paths.
- For failures, scan the failure signatures below before touching state.
- For migrations, review `cortex/migrations/core.py` and
  `cortex/migrations/registry.py`; abort if rollback or downgrade behavior is
  unclear.

Never revert unrelated user or concurrent work.

## Critical Paths

- `cortex/engine/`: write path, guards, transactions, snapshots.
- `cortex/ledger/`: hash chains, signatures, writers, verifiers.
- `cortex/migrations/`: schema evolution, registry, rollback behavior.
- `cortex/memory/`: tenant isolation, fact aging, memory ledger, retrieval.
- `cortex/guards/`: deterministic admission and rejection boundaries.
- `cortex/verification/`: formal and deterministic validation.
- `cortex/routes/`: external API contracts and tenant-scoped reads/writes.
- `cortex/extensions/daemon/`: background loops and async resource safety.
- `cortex/extensions/llm/`: provider boundaries, caching, conjecture handling.

Scoped files currently exist for:

- `cortex/engine/AGENTS.md`
- `cortex/guards/AGENTS.md`
- `cortex/ledger/AGENTS.md`
- `cortex/memory/AGENTS.md`
- `cortex/migrations/AGENTS.md`
- `cortex/routes/AGENTS.md`
- `cortex/verification/AGENTS.md`

## Write Path

For facts, runtime state, ledgered decisions, and other persisted domain state:

```text
Proposal -> Guards -> Taint if required -> Schema/Types
         -> Encryption if sensitive -> Ledger/Audit where implemented
         -> Transactional persistence -> Index/cache side effects
```

Rules:

- Fail closed on validation, taint, tenant, schema, encryption, or ledger errors.
- Prefer one database transaction for coupled ledger and persistence writes.
- For side effects outside the transaction, document explicit compensation.
- Capture snapshots only where the implementation provides snapshot semantics.
- Treat committed facts and ledger records as immutable.

`CORTEX-TAINT` is an admission/provenance token unless a route implements
cryptographic signature verification. It is mandatory only where the route or
model currently enforces it. Do not claim universal taint enforcement without
tests.

Relevant tests include:

```bash
pytest tests/test_store_request_taint.py \
       tests/test_causality_taint.py \
       tests/test_taint_propagation.py \
       tests/test_taint_preserves_encryption.py -v
```

## Read Path

- Public reads must be scoped to the authenticated or explicit `tenant_id`.
- Multi-tenant/admin reads require explicit authority and traceable scope.
- Facts returned from tainted/provenance-critical sources must not strip taint or
  provenance metadata when the response type can carry it.
- Read caches that can serve facts must include tenant scope in the key and must
  document invalidation or TTL behavior.
- Derived inferences from reads remain conjecture unless persisted through the
  write path.
- Ledger verification must run over a consistent snapshot or transaction; do not
  assert generic SQL isolation levels without mapping them to the backend.

## Coding Rules

- Add type hints to public functions and changed public surfaces.
- Catch specific exceptions in core paths; broad boundary catches require a
  rationale and must not hide validation failures.
- Do not use `time.sleep()` inside async code; use `asyncio.sleep()`.
- Do not use bare `print()` in core paths; use logging or Rich at CLI edges.
- Do not use `float` for money, persisted trust scores, deterministic thresholds,
  or consensus decisions. Embeddings, vector math, and ML metrics may use floats.
- Keep CLI modules thin. Business logic belongs in package modules such as
  `cortex/engine/`, `cortex/services/`, or domain-specific packages.
- Do not document a named module, command, or capability unless it exists.

## Validation

Every behavior change needs focused tests or an equivalent executable check.
Run the smallest relevant set first, then broaden when touching shared paths.

Baseline checks:

```bash
ruff check cortex/
pyright cortex/
git diff --check
```

Focused trust checks:

```bash
pytest tests/test_guard_pipeline.py \
       tests/test_daemon_guarded_persistence.py -v

pytest tests/test_ledger_integrity_verification.py \
       tests/test_ledger_checkpointing.py \
       tests/test_ledger_schema_compat.py \
       tests/test_ledger_tenant_hash_binding.py \
       tests/test_ledger_l3.py \
       tests/test_migrations_core.py -v
```

When changing ledger behavior, verify the relevant chain:

```bash
cortex trust-ledger verify
```

If the `cortex` entrypoint is unavailable in the environment, use the matching
module or test-level verifier and state that limitation.

For trust-sensitive changes, document impact on:

- tenant isolation
- taint/provenance
- encryption and key handling
- ledger/hash continuity
- rollback or compensation
- telemetry/log redaction

## Failure Signatures

Treat these as high-signal audit findings:

- `time.sleep()` inside `async def`.
- Bare `print()` in `cortex/engine/`, `cortex/memory/`, or `cortex/guards/`.
- Broad `except Exception` in core paths that hides deterministic failures.
- Ledger write with no prior guard or tenant validation in the call path.
- Schema change with no migration registry entry or rollback review.
- Missing taint on a route that explicitly requires taint.
- Plaintext secret, key, token, PII, prompt, or tenant payload in metadata,
  logs, docs, telemetry, or ledger records.
- CLI command containing business logic that belongs in package modules.

## References

- `README.md` - project overview and install surface.
- `docs/AXIOMS.md` - full axiom documentation.
- `docs/SECURITY_TRUST_MODEL.md` - trust boundaries and audit model.
- `docs/architecture.md` - system topology and module map.
- `docs/OPERATIONS.md` - runtime and maintenance procedures.
- `docs/CONTRIBUTING.md` - contribution workflow.
