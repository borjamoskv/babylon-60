---
title: "CORTEX Native Technologies"
description: "Canonical definition of the five CORTEX-native trust technologies"
status: canonical
version: 1.0
last_updated: 2026-04-07
authors:
  - Borja Moskv
tags:
  - cortex
  - trust-layer
  - ledger
  - taint
  - verification
  - autopoiesis
---

# CORTEX Native Technologies

This page defines five CORTEX-native technologies. They are not separate products, not replacement package names, and not marketing labels. They are higher-order capabilities that emerge from the composition of existing CORTEX modules.

The claim is narrow and technical:

- conventional memory stacks may provide storage, retrieval, or logging
- CORTEX composes deterministic admission, taint attribution, cryptographic continuity, rollback-aware mutation, and self-modifying containment in one trust boundary
- that composition creates capabilities that behave like distinct technologies inside the system

## The Five Technologies At A Glance

| Technology | Core question it answers | Primary surfaces |
| :--- | :--- | :--- |
| **Persistent Cryptoepistemology** | Should a generated claim be allowed to become state? | `cortex/guards`, `cortex/verification`, `cortex/services/trust.py` |
| **Hash Continuity Forensics** | Can we prove the chain of custody was not altered? | `cortex/ledger`, `cortex/memory/ledger.py`, `cortex/engine/snapshots.py` |
| **Encapsulated Conjectural Memory** | Can uncertain knowledge exist without posing as truth? | `cortex/memory`, `cortex/extensions/causality`, `cortex/routes/facts.py` |
| **Autonomous Integrity Sagas** | Can a mutation fail safely at any step? | Root `AGENTS.md`, `cortex/engine/snapshots.py`, `cortex/ledger/writer.py` |
| **Verified Agent Autopoiesis** | Can agents synthesize new logic without bypassing trust? | `cortex/extensions/swarm/code_smith.py`, `cortex/extensions/swarm/verification_gate.py`, `cortex/extensions/swarm/worktree_isolation.py` |

## Admission Rule

A capability qualifies as CORTEX-native only if it satisfies all of the following:

1. Generated output is treated as conjecture until deterministic validation passes.
2. Every persisted mutation can be traced through a cryptographic continuity primitive.
3. Taint, confidence, or integrity state survives both writes and reads.
4. Failure can abort or roll back without leaving silent partial state behind.
5. Agent self-modification, if present, is isolated and verified before touching trust-critical surfaces.

---

## 1. Persistent Cryptoepistemology

**Persistent Cryptoepistemology** is the CORTEX discipline for deciding when generated output deserves to exist as durable system state.

It is not a classifier and not a confidence score. It is an admission membrane.

### Operational problem

LLMs generate plausible strings. Databases persist bytes. Neither layer answers the trust question:

> "Should this proposition be allowed to mutate system reality?"

CORTEX answers that question with deterministic structure instead of model self-confidence.

### Operational mechanism

```text
Proposal
  -> Guard evaluation
  -> CORTEX-TAINT attribution
  -> Schema / type / contract validation
  -> Verification and trust checks
  -> Ledger emission
  -> Persistence
```

Relevant surfaces:

- `cortex/guards/taint.py` generates and verifies `taint:{agent_id}:{session_id}:{timestamp}:{sha3_256}`
- `cortex/guards/*` provides admission boundaries for paths, contradictions, capabilities, thermodynamics, and hygiene
- `cortex/verification/oracle.py` and `cortex/services/trust.py` provide verification and integrity checks
- root `AGENTS.md` defines the unidirectional Write-Path contract

### Why it is a distinct technology

Persistent Cryptoepistemology turns "model output" into a governed state transition with provenance. The system is no longer asking whether text sounds right. It is asking whether the proposal crossed the required membrane.

### Failure condition

The technology is considered bypassed if any persisted fact:

- enters durable state without guards
- lacks a valid `CORTEX-TAINT`
- downgrades a validation error into a permissive write

---

## 2. Hash Continuity Forensics

**Hash Continuity Forensics** is the CORTEX method for proving that a memory or event thread preserved causal continuity over time.

This is not just "we store hashes." It is a forensic discipline for continuity, replay, checkpointing, and post-incident proof.

### Operational problem

Most systems can tell you what rows exist now. They struggle to prove:

- what the prior state was
- whether an edit happened silently
- where the continuity break occurred
- which snapshot corresponds to which ledger horizon

### Operational mechanism

Relevant surfaces:

- `cortex/ledger/writer.py` links each new event to the previous hash before enqueueing downstream enrichment
- `cortex/ledger/verifier.py` recomputes hashes, checks `prev_hash`, validates payload consistency, and reports chain breaks
- `cortex/ledger/ledger_core.py` builds Merkle checkpoints and O(log N) proofs
- `cortex/memory/ledger.py` keeps tenant-scoped L3 event continuity
- `cortex/engine/snapshots.py` binds rollback material to transaction and Merkle state

### What it produces

- tamper evidence instead of optimistic logging
- chain-break localization instead of vague corruption suspicion
- checkpoint-based verification instead of full-chain rehash for every proof
- rollback evidence that still belongs to a verified continuity horizon

### Failure condition

Hash Continuity Forensics fails if any of the following occur:

- stored `prev_hash` diverges from expected chain state
- payload hash and row hash disagree
- recomputed event hash differs from stored hash
- snapshot restoration cannot be tied back to a known transaction boundary

---

## 3. Encapsulated Conjectural Memory

**Encapsulated Conjectural Memory** is the CORTEX memory discipline that allows uncertain, stale, derived, or contaminated knowledge to exist without masquerading as verified truth.

The key idea is not to ban conjecture. It is to contain it.

### Operational problem

A useful agent needs working hypotheses. A trustworthy system cannot let those hypotheses silently impersonate facts.

Without containment:

- stale retrieval looks like truth
- contradictions stay unresolved
- low-confidence derivations contaminate descendants
- callers infer certainty from mere presence

### Operational mechanism

Relevant surfaces:

- `cortex/memory/void_detector.py` classifies result topology into `CONFIDENT`, `FOG_ZONE`, `VOID_ABSOLUTE`, `STALE_KNOWLEDGE`, or `CONTRADICTION`
- `cortex/extensions/causality/taint.py` propagates `CLEAN`, `SUSPECT`, and `TAINTED` across the causal DAG
- `cortex/memory/ledger.py` preserves immutable event history for replay
- `cortex/routes/facts.py` and the public memory surface keep reads tenant-scoped and writes guarded
- root `AGENTS.md` Read-Path contract requires taint propagation and forbids speculative reconstruction

### What it changes

Conjecture becomes a first-class memory state instead of a hidden bug:

- uncertain knowledge can remain queryable
- contradictory knowledge can be flagged before response generation
- tainted descendants can be downgraded before they cause damage
- the read path preserves epistemic state instead of laundering it away

### Failure condition

Encapsulation is broken if:

- taint metadata is stripped on read
- a tainted or suspect derivation is persisted as clean
- contradiction or void signals are ignored and presented as confident knowledge

---

## 4. Autonomous Integrity Sagas

**Autonomous Integrity Sagas** is the mutation discipline that makes non-trivial writes reversible, auditable, and fail-stop.

It is the operational answer to a hard requirement:

> "If the trust path fails halfway through, the system must not pretend the mutation succeeded."

### Operational problem

Real trust failures happen in the middle:

- a guard passes but schema validation fails
- persistence succeeds but side effects fail
- an index update diverges after the ledger event is emitted
- a rollback is triggered after part of the pipeline already advanced

### Operational mechanism

The root `AGENTS.md` defines the write path as a Saga:

```text
Guards
  -> Taint
  -> Schema and type validation
  -> Encryption
  -> Ledger emission
  -> Persistence
  -> Index and side effects
```

With compensating actions in reverse order on failure.

Relevant surfaces:

- root `AGENTS.md` specifies the Saga contract and abort semantics
- `cortex/engine/snapshots.py` provides snapshot creation and restoration around mutation horizons
- `cortex/ledger/writer.py` and `cortex/memory/ledger.py` provide append-only continuity around mutation records
- `cortex/guards/taint.py` provides deterministic attribution before persistence

### What it changes

Autonomous Integrity Sagas turn trust from a best-effort pipeline into a transactional discipline:

- every forward action implies a compensating path
- rollback has explicit material, not just intent
- partial writes are treated as failures, not as acceptable residue

### Failure condition

The Saga discipline is violated if:

- a write mutates state before the required guard or taint step
- rollback depends on manual reconstruction instead of a defined compensation path
- snapshots are missing for state that claims rollback safety

---

## 5. Verified Agent Autopoiesis

**Verified Agent Autopoiesis** is the CORTEX capability that allows agents to synthesize, test, and introduce new logic without letting self-modification bypass trust boundaries.

This is not unrestricted self-editing. It is self-editing under containment.

### Operational problem

An autonomous system that can never rewrite itself stagnates.
An autonomous system that rewrites itself without isolation becomes an attack surface.

CORTEX treats that tension as an engineering surface, not as a philosophical slogan.

### Operational mechanism

Relevant surfaces:

- `cortex/extensions/swarm/code_smith.py` defines the safe ASE pipeline: `REQUEST -> DESIGN -> EDIT -> VALIDATE -> TEST -> COMMIT`
- `cortex/extensions/swarm/verification_gate.py` classifies proposal risk and rejects structural debt on critical paths
- `cortex/extensions/swarm/worktree_isolation.py` provides isolated worktree-style execution contexts
- `scripts/sortu/sortu_jit_executor.py` supports memory-only AST execution for bounded JIT validation

### What it changes

Verified Agent Autopoiesis means CORTEX agents can evolve while remaining governable:

- proposals are isolated before they touch trust-critical code
- generated logic is validated before it becomes durable behavior
- rollback remains available through known-good state and staged progression

### Failure condition

Autopoiesis is unverified if:

- generated code touches core state without isolation
- a proposal skips validation or testing and still reaches commit state
- a critical-path proposal ships with explicit structural debt markers such as `TODO` or `HACK`

---

## Composition Effect

None of the five technologies is sufficient alone.

Their value comes from composition:

- **Persistent Cryptoepistemology** decides whether a proposition may cross the boundary.
- **Hash Continuity Forensics** proves the resulting history stayed intact.
- **Encapsulated Conjectural Memory** keeps uncertainty visible after storage and retrieval.
- **Autonomous Integrity Sagas** ensures failure leaves reversible, auditable state.
- **Verified Agent Autopoiesis** allows the system to change itself without disabling the first four.

That composition is the actual CORTEX differentiator: generated state becomes governed state, and governed state remains auditable even as the system evolves.

## Relationship To Other Docs

- [Architecture](architecture.md)
- [System Map](system-map.md)
- [CORTEX Capabilities](CORTEX-CAPABILITIES.md)
- [CORTEX System Brief](cortex-system-brief.md)
