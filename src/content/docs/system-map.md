---
title: "System Map"
description: "Canonical CORTEX subsystem hierarchy and package map"
status: canonical
version: 1.0
last_updated: 2026-04-07
---

# CORTEX System Map

This page defines the canonical subsystem hierarchy for the current repository. It does not rename packages; it groups the existing `cortex/` surface into five stable architectural layers. After the full name has been established, documents may use the short form without the `CORTEX` prefix.

| Subsystem | Purpose | Primary package areas |
| :--- | :--- | :--- |
| `CORTEX Hypercore` | Trust kernel, persistence, and verification boundary | `cortex/engine`, `cortex/ledger`, `cortex/guards`, `cortex/verification`, `cortex/crypto`, `cortex/database`, `cortex/storage`, `cortex/auth`, `cortex/security` |
| `CORTEX Overmind` | Orchestration, routing, agent coordination, and consensus | `cortex/agents`, `cortex/consensus`, `cortex/gateway`, `cortex/mcp`, `cortex/worker`, `cortex/extensions/swarm`, `cortex/extensions/sovereign`, `cortex/extensions/federation`, `cortex/extensions/hypervisor`, `cortex/extensions/manifold` |
| `CORTEX Deepforge` | Synthesis, reasoning, generation, and cognitive tooling | `cortex/composer`, `cortex/mcts`, `cortex/shannon`, `cortex/extensions/llm`, `cortex/extensions/thinking`, `cortex/extensions/evolution`, `cortex/extensions/training`, `cortex/extensions/skills`, `cortex/extensions/perception` |
| `CORTEX Primeflow` | Runtime execution, delivery surfaces, and operational control | `cortex/api`, `cortex/routes`, `cortex/services`, `cortex/events`, `cortex/http`, `cortex/cli`, `cortex/telemetry`, `cortex/extensions/automation`, `cortex/extensions/daemon`, `cortex/extensions/sync`, `cortex/extensions/notifications`, `cortex/extensions/timing` |
| `CORTEX Coreshift` | Memory evolution, indexing, compaction, and schema/state transitions | `cortex/memory`, `cortex/facts`, `cortex/search`, `cortex/embeddings`, `cortex/graph`, `cortex/compaction`, `cortex/enrichment`, `cortex/migrations`, `cortex/audit`, `cortex/compliance`, `cortex/forensics` |

## Canonical Notes

- `CORTEX Hypercore` is the trust boundary: if a change affects write integrity, tenant isolation, or verification, it belongs here first.
- `CORTEX Overmind` coordinates distributed behavior, but it does not own persistence semantics.
- `CORTEX Deepforge` produces or transforms plans, models, and tools; it should not bypass guards.
- `CORTEX Primeflow` is the execution surface for APIs, CLI, daemons, and runtime connectors.
- `CORTEX Coreshift` covers controlled evolution of memory and schema, including migrations and compaction.

## Relationship To Other Docs

- [Architecture](architecture.md)
- [CORTEX Overview](index.md)
- [CORTEX Capabilities](CORTEX-CAPABILITIES.md)
