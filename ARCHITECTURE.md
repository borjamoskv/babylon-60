# CORTEX Architecture

## Package Structure

CORTEX follows a three-layer architecture. Only **Core** modules are part of the supported product contract.

### 🟢 Core — Supported Product

These modules form the stable, supported surface of CORTEX:

| Module | Purpose |
|--------|---------|
| `cortex/core/` | CortexEngine — main entry point |
| `cortex/memory/` | Persistent memory management |
| `cortex/ledger/` | SHA-256 hash-chained ledger |
| `cortex/crypto/` | Cryptographic primitives |
| `cortex/database/` | SQLite/aiosqlite layer |
| `cortex/storage/` | Storage abstraction |
| `cortex/search/` | Vector search + FTS |
| `cortex/facts/` | Temporal facts |
| `cortex/verification/` | Integrity verification |
| `cortex/audit/` | Audit trail |
| `cortex/security/` | Privacy Shield, AST Sandbox |
| `cortex/auth/` | RBAC, API keys, JWT |
| `cortex/types/` | Pydantic models |
| `cortex/migrations/` | Schema migrations |
| `cortex/guards/` | Quality seals & guardrails |
| `cortex/utils/` | Shared utilities |
| `cortex/cli/` | CLI interface |

### 🔵 Integrations — Optional Extras

Installed via `pip install cortex-persist[extra]`:

| Module | Extra | Purpose |
|--------|-------|---------|
| `cortex/api/` | `[api]` | FastAPI REST API |
| `cortex/routes/` | `[api]` | Route handlers |
| `cortex/http/` | `[api]` | HTTP middleware |
| `cortex/mcp/` | `[mcp]` | Model Context Protocol server |
| `cortex/adk/` | `[adk]` | Google ADK integration |
| `cortex/embeddings/` | `[embeddings]` | Sentence transformers |
| `cortex/worker/` | `[daemon]` | Background workers |

### 🟠 Experimental — Research & Unstable

> ⚠️ These modules may change or be removed without notice. Do not depend on them in production.

| Module | Purpose |
|--------|---------|
| `cortex/experimental/shannon/` | Information-theoretic entropy & exergy scoring |
| `cortex/experimental/mcts/` | Monte Carlo Tree Search for git operations |
| `cortex/experimental/composer/` | Vision QA & manifesto generation |
| `cortex/experimental/darknet/` | Social media monitoring agents |
| `cortex/experimental/mac_maestro/` | macOS automation executor |
| `cortex/consensus/` | Byzantine BFT consensus (beta) |
| `cortex/swarm/` | Multi-agent swarm orchestration (beta) |
| `cortex/forensics/` | Forensic analysis tools (beta) |
| `cortex/graph/` | Knowledge graph (beta) |
| `cortex/enrichment/` | Data enrichment pipeline (beta) |
| `cortex/compliance/` | EU AI Act compliance (beta) |

### 📦 Extensions

Internal extensions live in `cortex/extensions/` and are loaded on demand.

## Dependency Philosophy

- **Core** depends only on: `sqlite-vec`, `aiosqlite`, `click`, `rich`, `keyring`, `cryptography`, `pydantic`
- **Integrations** add their own dependencies via extras
- **Experimental** modules must never be imported by Core
