# MCP Operator Workflow

This is the recommended operating model for keeping Antigravity and CORTEX
below client-side MCP tool ceilings.

## Baseline

Keep the default active stack tiny:

- `github-mcp-server`
- `perplexity-ask`
- `cortex-summary`

That baseline is for everyday coding, code review, and lightweight ledger
visibility. Treat it as the long-lived profile.

## Overlays

Enable overlays only for the duration of the task that needs them:

- `docs-pack`: `notion-mcp-server`
- `gcp-pack`: `gke-oss`, `cloudrun`, `StitchMCP`, `genkit-mcp-server`
- `cortex-deep-pack`: `cortex-readonly`, `cortex-graph`, `cortex-core`, `cortex-trust`, `cortex-ops`, `cortex-media`, `cortex-research`
- `vcs-ui-pack`: `GitKraken`

Do not enable multiple packs by default. Start from baseline, add one pack,
finish the task, then drop back to baseline.

## Native CORTEX Profiles

The native MCP server supports:

- `core`
- `trust`
- `ops`
- `media`
- `research`

Prefer separate MCP entries such as `cortex-core` and `cortex-trust` instead
of one server that tries to expose every family at once.

## Toolbox Profiles

For Toolbox-backed read access:

- `cortex-summary` exposes `cortex-stats` only
- `cortex-readonly` exposes the 5 read-mostly query tools
- `cortex-graph` exposes the 3 recursive/analysis tools
- `full` keeps the canonical `tools.yaml` with named toolsets for internal use

The launcher defaults to `summary`:

```bash
TOOLBOX_MODE=stdio bash cortex/mcp/toolbox/run_toolbox.sh
```

Use `TOOLBOX_PROFILE=readonly`, `graph`, or `full` only when needed.

## Secret Handling

- Never store a literal PAT or API token inside active MCP JSON config.
- Feed GitHub auth via `GITHUB_PERSONAL_ACCESS_TOKEN` or a shell-based fallback such as `gh auth token`.
- Keep Notion and Stitch on env-backed auth only.
- If a secret was ever committed to local config, revoke or rotate it immediately after cleanup.
