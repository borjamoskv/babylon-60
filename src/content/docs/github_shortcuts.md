---
title: "GitHub Shortcuts"
description: "Shortcut commands for navigating common GitHub workflows from the CORTEX CLI."
---

# GitHub Shortcuts

`cortex github` now exposes a set of navigation helpers for common GitHub workflows that are normally hidden behind browser shortcuts or URL tricks.

## URL shortcuts

```bash
cortex github dev cortex/cli/github_cmds.py --open
cortex github permalink cortex/cli/github_cmds.py --lines 10-25
cortex github search "store_fact" --path cortex/engine --lang python --symbol CortexEngine
cortex github diff-url --pr 42 --format patch
cortex github review 42 --open
cortex github blame cortex/cli/github_cmds.py --open
cortex github history cortex/cli/github_cmds.py --open
```

## GitHub CLI wrappers

```bash
cortex github pr checkout 123
cortex github pr view 123 --web
cortex github pr create --fill --draft
cortex github repo clone owner/repo
cortex github agent-demo --op status
cortex agent github-repl
```

These commands keep the URL-building logic out of the shell and make the most useful GitHub tricks scriptable from the repository context.

## GitHub Agent

The agent runtime also exposes a `GitHubAgent` builtin for swarm workflows.
It accepts `TASK_REQUEST` payloads with ops such as `status`, `dev`,
`permalink`, `search`, `diff_url`, `review`, `blame`, `history`,
`pr_checkout`, `pr_view`, `pr_create`, and `repo_clone`.
