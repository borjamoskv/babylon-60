# MCP Toolbox for Databases — CORTEX Integration

Expose `cortex.db` as read-only MCP tools for Codex, Claude Desktop, Gemini CLI, or any Toolbox-compatible client.

## Architecture

```text
Agent → MCP Protocol → Toolbox (HTTP or stdio) → cortex.db (reads)
Agent → MCP Protocol → CORTEX MCP Server      → cortex.db (writes)
```

## Canonical Config

The supported Toolbox config lives at:

```text
cortex/mcp/toolbox/tools.yaml
```

It uses the current flat Toolbox format so named toolsets such as `cortex-readonly`, `graph-analysis`, and `cortex-summary` are available on recent Toolbox releases.

Compact client entrypoints also live alongside it:

```text
cortex/mcp/toolbox/cortex-summary.yaml
cortex/mcp/toolbox/cortex-readonly.yaml
cortex/mcp/toolbox/cortex-graph.yaml
```

## Install

Any of these work:

```bash
go install github.com/googleapis/genai-toolbox@latest
```

```bash
npx -y @toolbox-sdk/server --help
```

## Quick Start

### HTTP mode

```bash
bash cortex/mcp/toolbox/run_toolbox.sh
```

The launcher now defaults to `TOOLBOX_PROFILE=summary` so the default client
footprint stays minimal.

Custom DB or port:

```bash
CORTEX_DB=/path/to/cortex.db TOOLBOX_PORT=8080 \
  bash cortex/mcp/toolbox/run_toolbox.sh
```

Use a deeper profile only when needed:

```bash
TOOLBOX_PROFILE=readonly TOOLBOX_MODE=stdio bash cortex/mcp/toolbox/run_toolbox.sh
```

```bash
TOOLBOX_PROFILE=graph TOOLBOX_MODE=stdio bash cortex/mcp/toolbox/run_toolbox.sh
```

```bash
TOOLBOX_PROFILE=full TOOLBOX_MODE=http bash cortex/mcp/toolbox/run_toolbox.sh
```

HTTP clients should connect to:

```text
http://127.0.0.1:5050/mcp
```

Named toolset endpoints are available only when you launch the canonical full config:

```bash
TOOLBOX_PROFILE=full TOOLBOX_MODE=http bash cortex/mcp/toolbox/run_toolbox.sh
```

Then these endpoints are available:

```text
http://127.0.0.1:5050/mcp/cortex-readonly
http://127.0.0.1:5050/mcp/graph-analysis
http://127.0.0.1:5050/mcp/cortex-summary
```

### stdio mode

Subprocess MCP clients such as Codex or Claude Desktop must launch Toolbox with `--stdio`.

```bash
TOOLBOX_MODE=stdio bash cortex/mcp/toolbox/run_toolbox.sh
```

Equivalent direct command:

```bash
CORTEX_DB="${HOME}/.cortex/cortex.db" \
  npx -y @toolbox-sdk/server \
  --stdio \
  --tools-file /absolute/path/to/cortex/mcp/toolbox/cortex-summary.yaml
```

## Available Tools

### `cortex-summary`

- `cortex-stats`

### `cortex-readonly`

- `query-facts`
- `query-ghosts`
- `query-decisions`
- `query-signals`
- `cortex-stats`

### `graph-analysis`

- `trace-impact`
- `cluster-signals`
- `ghost-mapping`

### `full`

- Uses the canonical `tools.yaml`
- Keeps named toolsets (`cortex-readonly`, `graph-analysis`, `cortex-summary`)
- Best for internal bridge use, not for the default client baseline

## Troubleshooting

If you see:

```text
Initialized 0 sources
```

Toolbox did not load the intended config file. Check that you passed `--tools-file` and that `CORTEX_DB` points at a real SQLite file.

If you see:

```text
context deadline exceeded
```

from a subprocess MCP client, Toolbox was usually launched in HTTP mode instead of stdio mode. Add `--stdio` or set `TOOLBOX_MODE=stdio`.

If you see warnings about `allowed-origins` or `allowed-hosts`, those are security warnings for HTTP mode, not the root cause of a startup timeout.
