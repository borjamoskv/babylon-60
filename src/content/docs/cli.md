---
title: "CLI Reference"
description: "CORTEX Persist Documentation — CLI Reference"
---


CORTEX provides **90+ commands** organized by function. Run `cortex --help` for the full list.

---

## Global Options

| Option | Description |
|:---|:---|
| `--version` | Show version and exit |
| `--help` | Show help and exit |
| `--db PATH` | Override database path (default: `~/.cortex/cortex.db`) |

---

## Core Commands

### `cortex init`

Initialize the CORTEX database with the full schema.

```bash
cortex init [--db PATH]
```

Safe to call multiple times — idempotent.

---

### `cortex store`

Store a fact with automatic hash-chain ledger entry and embedding.

```bash
cortex store PROJECT CONTENT [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `PROJECT` | *required* | Project namespace |
| `CONTENT` | *required* | Fact content |
| `--type` | `knowledge` | `knowledge`, `decision`, `ghost`, `preference`, `identity`, `issue`, `error`, `bridge`, `world-model`, `counterfactual` |
| `--tags` | — | Comma-separated tags |
| `--confidence` | `stated` | `C1`, `C2`, `C3`, `C4`, `C5`, `stated`, `inferred` |
| `--source` | auto-detected | Source agent or process |
| `--ai-time` | — | Estimated AI time saved (Chronos integration) |
| `--complexity` | — | `low`, `medium`, `high`, `god`, `impossible` |

**Example:**

```bash
cortex store my-api "Rate limit is 100 req/min per API key" \
  --type knowledge --tags "api,limits" --source "agent:claude"
```

---

### `cortex search`

Semantic search across all facts using vector embeddings.

```bash
cortex search QUERY [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `--project`, `-p` | — | Scope to project |
| `--top`, `-k` | `5` | Number of results |
| `--scope`, `-s` | `core` | Search partition: `core`, `personal`, `cold`, `all` |
| `--epistemic` | `false` | Show void/fog/stale analysis overlay |

Uses `all-MiniLM-L6-v2` embeddings via ONNX Runtime for sub-5ms vector search.

---

### `cortex recall`

Load full context for a project.

```bash
cortex recall PROJECT [--db PATH]
```

Returns all active facts grouped by type (knowledge, decisions, errors, etc.).

---

### `cortex history`

Temporal query: what did we know at a specific time?

```bash
cortex history PROJECT [--at TIMESTAMP] [--db PATH]
```

---

### `cortex status`

Show CORTEX health and statistics.

```bash
cortex status [--json]
```

Displays: total facts, active facts, embeddings, transactions, DB size, projects.

---

### `cortex list`

List active facts in a table.

```bash
cortex list [--project PROJECT] [--type TYPE] [--limit N] [--tenant-id TENANT]
```

---

### `cortex edit`

Edit a fact (deprecates old, creates new with same metadata).

```bash
cortex edit FACT_ID NEW_CONTENT [--tenant-id TENANT]
```

---

### `cortex delete`

Soft-delete a fact (mark as deprecated).

```bash
cortex delete FACT_ID [-r TEXT] [--tenant-id TENANT]
```

---

## Trust & Verification Commands

### `cortex verify`

Cryptographic verification certificate for a single fact.

```bash
cortex verify FACT_ID
```

Output includes: hash chain status, Merkle root, consensus score, timestamp.

---

### `cortex trust-ledger`

Ledger operations.

```bash
cortex trust-ledger verify       # Full hash chain integrity check
cortex trust-ledger checkpoint   # Create Merkle checkpoint
```

---

### `cortex compliance-report`

Generate EU AI Act Article 12 compliance snapshot.

```bash
cortex compliance-report
```

Outputs: compliance score (0-5), requirement mapping, evidence references.

---

### `cortex audit`

View audit trail entries or run selected audit helpers.

```bash
cortex audit --project PROJECT --limit N
```

---

### `cortex vote`

Cast a consensus vote on a fact.

```bash
cortex vote FACT_ID 1 --agent AGENT_ID      # verify
cortex vote FACT_ID -1 --agent AGENT_ID     # dispute
```

---

## Sync & Export Commands

### `cortex sync`

Synchronize `~/.agent/memory/` JSON files → CORTEX DB (incremental, SHA-256 change detection).

```bash
cortex sync
```

---

### `cortex export`

Export a markdown snapshot for agent consumption.

```bash
cortex export [--out PATH]
```

Default output: `~/.cortex/context-snapshot.md`

---

### `cortex writeback`

Write-back: CORTEX DB → `~/.agent/memory/` JSON files.

```bash
cortex writeback
```

---

### `cortex migrate`

Import data from older versions.

```bash
cortex migrate [--source PATH]
```

---

## Time Tracking Commands

### `cortex time`

Show time tracking summary (WakaTime-like).

```bash
cortex time [--project PROJECT] [--days N]
```

---

### `cortex heartbeat`

Record an activity heartbeat for automatic time tracking.

```bash
cortex heartbeat PROJECT [ENTITY] [--category CATEGORY] [--branch BRANCH]
```

---

### `cortex timeline`

Navigate the CORTEX timeline and manage snapshots.

```bash
cortex timeline log
cortex timeline checkout TX_ID
cortex timeline snapshot --help
```

---

## Memory Intelligence Commands

### `cortex compact`

Run auto-compaction strategies on project memory.

```bash
cortex compact PROJECT [--strategy dedup|merge_errors|staleness_prune|ttl_prune|drift_check]
```

---

## Agent & Swarm Commands

### `cortex handoff`

Structured agent-to-agent context transfer.

```bash
cortex handoff generate
cortex handoff load
```

---

### `cortex ghost`

Desktop/system control via the GHOST-1 command family.

```bash
cortex ghost status
cortex ghost window --help
cortex ghost hand --help
```

---

### `cortex swarm`

Multi-agent swarm coordination.

```bash
cortex swarm up
cortex swarm board
cortex swarm audit PATH
```

---

## Infrastructure Commands

### `moskv-daemon`

Background daemon management.

```bash
moskv-daemon start         # Start the watchdog daemon
moskv-daemon check         # Run checks once
moskv-daemon config        # Show daemon config path and supported keys
moskv-daemon config --validate
moskv-daemon install       # Install as system service
moskv-daemon status        # Check daemon health
```

The daemon runs 13 specialized monitors: site health, SSL certs, disk space, ghost detection, security scanning, and more.
Persistent daemon settings live in `~/.cortex/daemon_config.json`; see
[Operations](OPERATIONS.md#daemon-configuration) for the supported autopoiesis
keys and an example config.

---

### `cortex mejoralo`

Code quality engine (X-Ray 13D scanner).

```bash
cortex mejoralo scan PROJECT PATH  # Analyze code quality
cortex mejoralo antipatterns
cortex mejoralo ship
```

---

### `cortex entropy`

Entropy monitoring for codebase health.

```bash
cortex entropy report
cortex entropy shannon
```

---

### `cortex purge`

Data cleanup operations.

```bash
cortex purge project PROJECT
cortex purge duplicates
```

---

### `cortex tips`

Developer tips and best practices engine.

```bash
cortex tips random
cortex tips -c security
```

---

### `cortex reflect`

Meta-cognitive session analysis.

```bash
cortex reflect PROJECT "Session summary"
```

---

## Makefile Shortcuts

```bash
make test          # Run all tests (60s timeout)
make test-fast     # Exclude slow tests (no torch imports)
make test-slow     # Only slow tests (graph RAG, embeddings)
make lint          # Run ruff linter
make format        # Auto-format with ruff
make docs          # Build mkdocs site
make serve-docs    # Live preview docs
```
