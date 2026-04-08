---
title: "Operations — CORTEX Persist"
description: "CORTEX Persist Documentation — Operations — CORTEX Persist"
---


Package: cortex-persist v0.3.0b2 · Engine: v8
License: Apache-2.0 · Python: >=3.10

> Runtime, maintenance, and troubleshooting procedures.
>
> Related: [`AGENTS.md`](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md) · [`architecture.md`](architecture.md)

---

## Environment Variables

```bash
GEMINI_API_KEY           # Google Gemini API key (LLM operations)
CORTEX_DB_PATH           # Primary DB path override (default: ~/.cortex/cortex.db)
CORTEX_DB                # Legacy DB path override
CORTEX_LOG_LEVEL         # DEBUG | INFO | WARNING | ERROR
CORTEX_ALLOWED_ORIGINS   # Comma-separated CORS allowlist
CORTEX_DEPLOY            # local | cloud
CORTEX_MASTER_KEY        # Base64 AES key fallback when OS keyring is unavailable
CORTEX_VAULT_KEY         # Alternate encryption key fallback
STRIPE_SECRET_KEY        # Stripe billing (optional: [billing])
REDIS_URL                # Redis connection (optional: [cloud])
TURSO_DATABASE_URL       # Turso edge database URL (optional: [cloud])
```

---

## Local Setup

```bash
# Install — editable with all optional deps
pip install -e ".[all]"

# Verify installation
cortex --help
```

### Optional Dependency Groups

| Extra | Installs | Purpose |
| --- | --- | --- |
| `[api]` | FastAPI, Uvicorn, httpx | REST API server |
| `[dev]` | pytest, pytest-cov, pytest-asyncio, httpx, z3-solver | Development & testing |
| `[adk]` | google-adk | Google Agent Development Kit |
| `[toolbox]` | toolbox-core | Toolbox integration |
| `[billing]` | stripe | Payment processing |
| `[cloud]` | asyncpg, redis, qdrant-client | Distributed backends |
| `[all]` | All of the above | Full installation |

---

## Entry Points

```text
cortex        → cortex.cli:cli          # Main CLI
moskv-daemon  → cortex.daemon_cli:main  # Background daemon
cortex-adk    → cortex.adk.runner:main  # Google ADK runner
```

---

## Running the API

```bash
# Development
uvicorn cortex.api:app --reload

# Production
uvicorn cortex.api:app --host 0.0.0.0 --port 8484 --workers 4
```

---

## Running the Daemon

```bash
# Start the background daemon
moskv-daemon start

# Check daemon status
moskv-daemon status
```

The daemon runs 13 monitors including health checks, compaction scheduling, sync operations, and integrity verification.

## Daemon Configuration

`moskv-daemon` reads persistent settings from `~/.cortex/daemon_config.json`.
Use CLI flags for one-off runs and the JSON file for recurring service installs
such as `launchd`, `systemd`, or Task Scheduler.

Example:

```json
{
  "sites": ["https://example.com/health"],
  "watch_path": "/path/to/workspace",
  "db_path": "/path/to/.cortex/cortex.db",
  "heartbeat_interval": 30.0,
  "frontier_metabolism_interval_hours": 12.0,
  "frontier_ingestion_interval_hours": 24.0,
  "zero_prompting_interval_hours": 24.0,
  "autopoiesis_interval_hours": 24.0,
  "autopoiesis_idle_poll_seconds": 60.0,
  "autopoiesis_target_score": 95,
  "autopoiesis_enable_healing": true,
  "autopoiesis_enable_manifestation": false,
  "autopoiesis_minimum_registered_tools": 0,
  "autopoiesis_project": "cortex",
  "autopoiesis_focus": "entropy"
}
```

A versioned example also lives at `configs/daemon_config.example.json` in the repository.

### Autopoiesis Keys

| Key | Default | Purpose |
| --- | --- | --- |
| `autopoiesis_interval_hours` | `24.0` | Minimum time between bounded autopoiesis cycles |
| `autopoiesis_idle_poll_seconds` | `60.0` | Sleep interval used while waiting for the next cycle |
| `autopoiesis_target_score` | `95` | `Mejoralo` score target below which healing is planned |
| `autopoiesis_enable_healing` | `true` | Allows bounded repair cycles through the existing healing path |
| `autopoiesis_enable_manifestation` | `false` | Allows tool generation and registration when explicitly enabled |
| `autopoiesis_minimum_registered_tools` | `0` | Threshold that can trigger tool manifestation when enabled |
| `autopoiesis_project` | `"cortex"` | Project namespace used when writing accepted cycles to the ledger |
| `autopoiesis_focus` | `"entropy"` | Planning focus passed into each cycle |

### Operational Notes

- The autopoiesis daemon is policy-driven. It does not run open-ended self-modification by default.
- `autopoiesis_enable_manifestation` stays disabled unless you want tool generation to be considered at all.
- Accepted cycles are logged with source `daemon:autopoiesis`.
- If no compatible engine write path is available, the daemon still runs but skips crystallization.

---

## CLI Operations

```bash
# Store a fact
cortex store PROJECT "content" --type decision --source agent:gemini

# Search facts
cortex search "query" -k 10

# Verify a fact and the trust ledger
cortex verify <FACT_ID>
cortex trust-ledger verify

# Export context snapshot
cortex export
```

---

## Database Migrations

```bash
# Migrations run automatically on startup.
# To run manually:
cortex migrate

# Migration files live in cortex/migrations/
# Never modify existing migration files — only add new ones.
```

---

## Backup & Restore

```bash
# The database is a single SQLite file.
# Default location: ~/.cortex/cortex.db

# Backup
cp ~/.cortex/cortex.db ~/.cortex/cortex.db.backup

# Restore
cp ~/.cortex/cortex.db.backup ~/.cortex/cortex.db
```

For AlloyDB/cloud deployments, use standard PostgreSQL backup procedures.

---

## Integrity Verification

```bash
# Verify a single fact
cortex verify <FACT_ID>

# Verify the ledger and view audit trail
cortex trust-ledger verify
cortex audit --limit 10
```

---

## Observability

| Component | Details |
| --- | --- |
| `telemetry/` | OpenTelemetry-compatible span tracing |
| `signals/` | Event bus for pub/sub, reactive signals |
| `notifications/` | macOS native notifications (Darwin-only) |
| `daemon/` | 13 monitors — scheduler, watchers, health |
| `hypervisor/` | Process supervision, crash recovery, watchdog |
| `timing/` | Performance timing, SLA tracking |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `LedgerIntegrityError` | Hash chain broken | Run `cortex trust-ledger verify` and `cortex verify FACT_ID` |
| Slow search | Missing embeddings | Verify embedding configuration and re-store or re-sync affected facts |
| Import errors | Missing optional deps | Install with `pip install -e ".[all]"` |
| Daemon crash loop | Stale PID file | Remove `~/.cortex/daemon.pid` |
| Encryption errors | Missing or rotated key | Check `CORTEX_MASTER_KEY`, `CORTEX_VAULT_KEY`, or OS keyring continuity |

---
