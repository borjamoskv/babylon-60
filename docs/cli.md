# CLI Reference

CORTEX provides **90+ commands** organized by function. Run `cortex --help` for the full list.

---

## Global Options

| Option | Description |
|:---|:---|
| `--version` | Show version and exit |
| `--help` | Show help and exit |
| `--db PATH` | Available on many subcommands such as `init`, `status`, `recall`, `history`, and trust commands |

---

## Core Commands

### `cortex init`

Initialize the CORTEX database with the full schema.

```bash
cortex init [--db PATH]
```

Safe to call multiple times — idempotent.

---

### `cortex memory store`

Store a fact with automatic hash-chain ledger entry and embedding.

```bash
cortex memory store PROJECT CONTENT [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `PROJECT` | *required* | Project namespace |
| `CONTENT` | *required* | Fact content |
| `--type` | `knowledge` | `knowledge`, `decision`, `error`, `ghost`, `config`, `bridge`, `axiom`, `rule` |
| `--tags` | — | Comma-separated tags |
| `--confidence` | `stated` | `C1`, `C2`, `C3`, `C4`, `C5`, `stated`, `inferred`, `verified` |
| `--source` | auto-detected | Source agent or process |
| `--ai-time` | — | Estimated AI time saved (Chronos integration) |
| `--complexity` | — | Task complexity (`low`, `medium`, `high`, `god`, `impossible`) |

**Example:**

```bash
cortex memory store my-api "Rate limit is 100 req/min per API key" \
  --type config --tags "api,limits" --source "agent:claude"
```

---

### `cortex memory search`

Semantic search across all facts using vector embeddings.

```bash
cortex memory search QUERY [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `--project`, `-p` | — | Scope to project |
| `--top`, `-k` | `5` | Number of results |
| `--as-of` | — | Point-in-time query (ISO 8601) |

Uses `all-MiniLM-L6-v2` embeddings via ONNX Runtime for sub-5ms vector search.

---

### `cortex memory recall`

Load full context for a project.

```bash
cortex memory recall PROJECT [--db PATH]
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
cortex list [--project PROJECT] [--type TYPE] [--limit N]
```

---

### `cortex edit`

Edit a fact (deprecates old, creates new with same metadata).

```bash
cortex edit FACT_ID NEW_CONTENT
```

---

### `cortex delete`

Soft-delete a fact (mark as deprecated).

```bash
cortex delete FACT_ID [--reason TEXT]
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

### `cortex vote-ledger`

Ledger operations.

```bash
cortex vote-ledger verify    # Full hash chain integrity check
```

---

### `cortex compliance-report`

Generate EU AI Act Article 12 compliance snapshot.

```bash
cortex compliance-report
```

Outputs: compliance score (0-5), requirement mapping, evidence references.

---

### `cortex audit-trail`

Generate a timestamped, hash-verified audit log.

```bash
cortex audit-trail [--project PROJECT] [--limit N]
```

---

### `cortex vote`

Cast a consensus vote on a fact.

```bash
cortex vote FACT_ID VALUE --agent AGENT_ID
```

Use `VALUE=1` to verify and `VALUE=-1` to dispute.

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

Visual temporal memory browsing.

```bash
cortex timeline log                  # View transaction ledger
cortex timeline checkout TX_ID       # Reconstruct state at a transaction
cortex timeline snapshot create NAME # Create a physical snapshot
```

---

## Memory Intelligence Commands

### `cortex compact`

Run auto-compaction strategies on project memory.

```bash
cortex compact PROJECT [--strategy dedup|merge|prune|all] [--dry-run]
```

---

### `cortex episode`

Episodic memory operations.

```bash
cortex episode observe                      # Capture session snapshot
cortex episode recall --project PROJECT     # Recover relevant episodes
cortex episode patterns --project PROJECT   # Detect recurring patterns
```

---

### `cortex context`

Context window management for agents.

```bash
cortex context infer [--persist]  # Infer current working context
cortex context signals            # Inspect ambient signals
cortex context history            # Review recent inferred contexts
```

---

## Agent & Swarm Commands

### `cortex handoff`

Structured agent-to-agent context transfer.

```bash
cortex handoff generate    # Generate handoff document
cortex handoff load        # Load the saved handoff
```

---

### `cortex ghost`

Ghost (incomplete work) management.

```bash
cortex ghost field --dir . # Scan active ghosts in a directory
cortex ghost status        # Check GHOST-1 dependencies
```

---

### `cortex swarm`

Multi-agent swarm coordination.

```bash
cortex swarm audit PATH    # Audit a file or directory with the swarm
cortex swarm refactor FILE # Refactor a file with the specialist swarm
cortex swarm up            # Start Omega Prime orchestration
```

---

## Infrastructure Commands

### `cortex mejoralo daemon`

Infinite sovereign improvement loop.

```bash
cortex mejoralo daemon     # Start the continuous MEJORAlo daemon
```

---

### `cortex autorouter`

AI model auto-selection daemon.

```bash
cortex autorouter start    # Start model routing
cortex autorouter stop     # Stop
cortex autorouter status   # Current model state
cortex autorouter history  # View switch history
```

---

### `cortex mejoralo`

Code quality engine (X-Ray 13D scanner).

```bash
cortex mejoralo scan PROJECT PATH                 # Analyze code quality
cortex mejoralo scan PROJECT PATH --auto-heal    # Attempt autonomous repair
cortex mejoralo awwwards-fix PROJECT PATH        # UI rewrite for Awwwards-grade polish
```

---

### `cortex entropy`

Entropy monitoring for codebase health.

```bash
cortex entropy report                # Immunity and entropy status report
cortex entropy shannon --project P   # Shannon entropy analysis
```

---

### `cortex purge`

Data cleanup operations.

```bash
cortex purge --project PROJECT [--before DATE] [--dry-run]
```

---

### `cortex tips`

Developer tips and best practices engine.

```bash
cortex tips [--category CATEGORY]
```

---

### `cortex reflect`

Meta-cognitive session analysis.

```bash
cortex reflect PROJECT "SUMMARY"     # Store a post-mortem reflection
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
