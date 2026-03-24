# CORTEX v8: Swarm Orchestration & Performance (Azkartu & Shannon)

This document specifies the architectural enhancements implemented in CORTEX v8 to support massive parallel agent deployments and sub-ms memory retrieval.

## 🌀 Squadron Orchestration (Swarm-100)

The v8 `SwarmManager` introduces the **Squadron Deployment Model**, allowing for task-isolated execution of specialized agent forces.

### Squad Taxonomy

- **P0: Mission Critical (Tactical)**: Synchronous execution, high-priority ledger writes, blocking verification.
- **P1: Strategic (Core)**: Asynchronous research, autonomous drift detection, background auditing.
- **P2: Maintenance (Shadow)**: Collective memory hygiene, ghost purging, and exergy extraction.

### Autonomous Recovery (Pulmones)

The `PulmonesWorker` daemon operates as a persistent OS-level process that:
1. Drains the failure queue (`idx_next_retry`).
2. Implements exponential backoff for failed tool calls.
3. Triggers memory hygiene cycles during idle periods.

---

## ⚡ Azkartu Performance (Ω-High)

To support 100+ parallel agents, the memory layer had to transition from disk-bound lookups to JIT-optimized retrieval.

### JIT Search Cache

The `SovereignVectorStoreL2` now features a **JIT Cache** for search results:

- **Mechanism**: Stores the results of hybrid search (BM25 + Vector) keyed by query-hash and project-ID.
- **Performance**: Latency drops from **~80ms to <1ms** on cache hits.
- **Invalidation**: L2 results are invalidated when the underlying SQLite store is mutated.

---

## 🧹 Shannon Compaction (Memory Hygiene)

As part of the **Law of Thermodynamics (Ω₂)**, CORTEX now actively fights informational entropy.

### ShannonCompactor

Integrated into the `PulmonesWorker` loop, the `ShannonCompactor`:

1. **Measures Entropy**: Calculates information density per project.
2. **Purges Redundancy**: Identifies semantically overlapping facts and consolidates microstates.
3. **Exergy Yield**: Ensures that only facts delivering non-negative exergy (useful work potential) persist in the long-term vault.

### Status

**CORTEX-Persist | Milestone 4: Performance & Alignment | v8.0-Alpha**
