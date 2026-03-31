# MCP Server

CORTEX implements the **Model Context Protocol (MCP)** — an open standard for connecting AI agents to tools and data sources. This makes CORTEX a plug-in for any MCP-compatible AI IDE.

---

## Compatible IDEs

| IDE | Status |
|:---|:---|
| **Claude Code** (Anthropic) | ✅ Native |
| **Cursor** | ✅ Native |
| **OpenClaw** | ✅ Native |
| **Windsurf** | ✅ Native |
| **Antigravity** | ✅ Native |

---

## Start the MCP Server

```bash
python -m cortex.mcp
```

Or explicitly:

```bash
python -m cortex.mcp.server
```

The server starts a stdio-based MCP transport, which is the standard for IDE integrations.

By default the native server now boots in the `core` tool profile. Use
`CORTEX_MCP_PROFILE` to opt into additional families without exposing the
entire tool surface at once.

---

## Configuration

### Claude Code (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.mcp"],
      "env": {
        "CORTEX_DB": "~/.cortex/cortex.db",
        "CORTEX_MCP_PROFILE": "core"
      }
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.mcp"],
      "env": {
        "CORTEX_MCP_PROFILE": "trust"
      }
    }
  }
}
```

### Antigravity (VS Code settings)

```json
{
  "mcp": {
    "servers": {
      "cortex-core": {
        "command": "python",
        "args": ["-m", "cortex.mcp"],
        "env": {
          "CORTEX_MCP_PROFILE": "core"
        }
      },
      "cortex-trust": {
        "command": "python",
        "args": ["-m", "cortex.mcp"],
        "env": {
          "CORTEX_MCP_PROFILE": "trust"
        }
      }
    }
  }
}
```

---

## Tool Profiles

The native MCP server is now budgeted by profile instead of exposing every
tool family by default.

| Profile | Tools |
|:---|:---|
| `core` | Store, search, status, ledger verification, causal trace, Shannon report, handoff, embeddings |
| `trust` | Audit trail, fact verification, compliance report, decision lineage, health checks |
| `ops` | Reality weaver, entropy cracker, temporal nexus, Genesis tools, scraper tools |
| `media` | Music engine and Suno headless generation |
| `research` | Hilbert-Omega theorem tooling |

Recommended usage:

- Use `core` for everyday coding sessions.
- Add `trust` when you need audit/compliance or health.
- Add `ops`, `media`, or `research` only for focused sessions.

The default active client stack should stay below a hard budget target of
`85` tools to preserve headroom under clients that cap total tools at `100`.

See [MCP Operator Workflow](mcp_operator_workflow.md) for the baseline and
overlay strategy.

---

## Core Tools

### `core`

| Tool | Description |
|:---|:---|
| `cortex_store` | Store a fact with automatic hash chaining and embedding |
| `cortex_search` | Hybrid semantic search across all facts |
| `cortex_status` | System health, statistics, and database info |
| `cortex_ledger_verify` | Full ledger integrity check — walks the entire hash chain |
| `cortex_trace_episode` | Trace causal episodes through persisted facts |
| `cortex_trace_chain` | Traverse up/down causal chains from a fact |
| `cortex_shannon_report` | Analyze structural entropy in persisted memory |
| `cortex_handoff` | Generate a session handoff summary |
| `cortex_embed` | Generate an embedding vector using the active provider |
| `cortex_embed_status` | Show embedding provider status |

### `trust`

| Tool | Description |
|:---|:---|
| `cortex_audit_trail` | Generate a timestamped, hash-verified audit log |
| `cortex_verify_fact` | Cryptographic verification certificate for a single fact |
| `cortex_compliance_report` | EU AI Act Article 12 compliance snapshot with score |
| `cortex_decision_lineage` | Trace how an agent arrived at any conclusion |
| `cortex_health_check` | Quick health score and grade |
| `cortex_health_report` | Full health report with recommendations |

### `ops`

| Tool | Description |
|:---|:---|
| `cortex_reality_weaver` | Build an architecture recommendation from project facts |
| `cortex_entropy_cracker` | Run filesystem entropy analysis on allowed paths |
| `cortex_temporal_nexus` | Summarize recent decision/ghost/signal activity |
| `cortex_genesis_*` | Generate or preview systems from declarative specs |
| `cortex_scrape*` | Scrape URLs and site maps through the sovereign scraper |

### `media`

| Tool | Description |
|:---|:---|
| `music_create_album` | Create a GRAMMY-Ω album concept |
| `music_generate_track` | Generate a track through the selected music adapter |
| `music_evaluate_gri` | Evaluate the Grammy Readiness Index of a track |
| `suno_generate_headless` | Generate a Suno track via headless extraction |

### `research`

| Tool | Description |
|:---|:---|
| `cortex_hilbert_omega` | Run Hilbert-Ω conjecture, millennium, or proof workflows |

---

## Tool Details

### `cortex_store`

**Parameters:**

| Param | Type | Required | Description |
|:---|:---|:---:|:---|
| `project` | string | ✅ | Project namespace |
| `content` | string | ✅ | Fact content |
| `fact_type` | string | — | `knowledge`, `decision`, `error`, `ghost`, `config`, `bridge` |
| `tags` | string | — | Comma-separated tags |
| `source` | string | — | Source identifier (auto-detected if omitted) |

**Example:**

```
Store this decision in CORTEX: "We chose PostgreSQL over MySQL for JSON support"
→ cortex_store(project="my-api", content="We chose PostgreSQL...", fact_type="decision")
```

### `cortex_search`

**Parameters:**

| Param | Type | Required | Description |
|:---|:---|:---:|:---|
| `query` | string | ✅ | Natural language search query |
| `project` | string | — | Filter by project |
| `top_k` | integer | — | Number of results (default: 5) |

### `cortex_compliance_report`

**Parameters:** None.

Returns a structured compliance report with:
- Compliance score (0-5)
- Per-article requirement status
- Evidence references
- Recommendations

---

## Privacy Shield

The MCP server includes the **Privacy Shield** — an ingress guard that scans all incoming data for secrets before storage:

- GitHub tokens (`ghp_`, `gho_`, `ghs_`)
- GitLab PATs (`glpat-`)
- JWT tokens
- SSH private keys
- Slack tokens (`xoxb-`, `xoxp-`)
- AWS credentials
- Generic API keys
- And 4 more patterns

If a secret is detected, the fact is flagged and the agent is notified. Critical secrets (private keys) force local-only storage regardless of configuration.

---

## Google ADK Integration

CORTEX also integrates with **Google Agent Developer Kit (ADK)**:

```bash
pip install cortex-persist[adk]
cortex-adk  # Start the ADK runner
```

This provides the same trust tools via the Google ADK toolbox bridge.

---

## Toolbox Bridge

For environments that use the Toolbox protocol:

```python
from cortex.mcp.toolbox_bridge import get_toolbox_tools

tools = get_toolbox_tools()
# Returns a list of tool definitions compatible with the Toolbox protocol
```
