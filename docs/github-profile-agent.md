# GitHub Profile Agent

This pattern makes the GitHub profile README a public projection of a real
CORTEX-backed agent.

The README is not the agent runtime. CORTEX is the memory and ledger. The README
only shows bounded, aggregate status.

## Architecture

```text
event or schedule
  -> profile-agent script
  -> CortexEngine.store(...)
  -> CORTEX transaction hash chain
  -> read-only ledger verification
  -> bounded README block update
  -> git commit/push to borjamoskv/borjamoskv
```

Use a local or self-hosted runner when you want the CORTEX database to remain
private. Do not commit a production CORTEX database to a public profile repo.

## Local Run

From a checkout of `Cortex-Persist`:

```bash
python3 scripts/profile_agent_bridge.py \
  --profile-repo-path /path/to/borjamoskv \
  --db ~/.cortex/profile-agent.sqlite \
  --json
```

The script:

- persists a heartbeat fact through `CortexEngine.store`;
- verifies the tenant-scoped CORTEX transaction hash chain;
- renders `assets/cortex-profile-agent.svg` as a static public status panel;
- renders `assets/cortex-profile-agent.status.json` as a machine-readable public contract;
- updates only the managed README block and generated status assets;
- publishes no raw memory, prompts, tenant payloads, or secrets.

## README Block

The script appends this managed block when it is missing:

```md
<!-- CORTEX-PROFILE-AGENT:START -->
...
<!-- CORTEX-PROFILE-AGENT:END -->
```

Only text inside those markers is overwritten.

The rendered block is intentionally more like a public console than a plain
status table: it includes a generated SVG panel, generated badges, a bounded
operational loop, public ledger signals, a SHA-256 public digest, a
machine-readable status JSON file, and a collapsible evidence packet. The values
are regenerated on each run from CORTEX state.

Disable the SVG panel with `--no-status-svg`, or change the generated asset path
with `--status-svg-path`. Disable the status JSON with `--no-status-json`, or
change its generated path with `--status-json-path`.

## Self-Hosted GitHub Actions Workflow

Put this in `borjamoskv/borjamoskv/.github/workflows/profile-agent.yml`.

```yaml
name: CORTEX Profile Agent

on:
  workflow_dispatch:
  schedule:
    - cron: "17 */6 * * *"

permissions:
  contents: write

jobs:
  project:
    runs-on: self-hosted
    steps:
      - name: Checkout profile repo
        uses: actions/checkout@v4

      - name: Checkout CORTEX Persist
        uses: actions/checkout@v4
        with:
          repository: borjamoskv/Cortex-Persist
          path: _cortex

      - name: Install CORTEX
        run: python3 -m pip install -e _cortex

      - name: Update README projection
        run: |
          python3 _cortex/scripts/profile_agent_bridge.py \
            --profile-repo-path . \
            --db "$HOME/.cortex/profile-agent.sqlite" \
            --profile-repo borjamoskv/borjamoskv \
            --source-repo borjamoskv/Cortex-Persist \
            --tenant public-profile \
            --project github-profile-agent \
            --agent-id cortex-profile-agent \
            --json

      - name: Commit projection
        run: |
          if git diff --quiet -- README.md assets/cortex-profile-agent.svg assets/cortex-profile-agent.status.json; then
            exit 0
          fi
          git config user.name "cortex-profile-agent"
          git config user.email "actions@users.noreply.github.com"
          git add README.md assets/cortex-profile-agent.svg assets/cortex-profile-agent.status.json
          git commit -m "chore: update CORTEX profile projection"
          git push
```

## Safety Rules

- Keep the CORTEX DB outside the public repo.
- Publish only aggregate ledger state, generated SVG/JSON output, and fact IDs.
- Use a dedicated tenant such as `public-profile`.
- Use a dedicated source such as `agent:cortex-profile-agent`.
- Treat README output as evidence of runtime state, not as the runtime itself.
