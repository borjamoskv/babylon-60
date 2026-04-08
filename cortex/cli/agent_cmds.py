"""CORTEX CLI — Agent commands (YAML-driven agent interface).

Commands:
    cortex.agents run --config role.yaml   — Run an agent from YAML
    cortex.agents validate --config role.yaml — Validate config
    cortex.agents init                      — Generate scaffold role.yaml
"""

from __future__ import annotations

import asyncio
import json
import shlex
import sys
from pathlib import Path

import click
from rich.table import Table

from cortex.cli.common import _run_async, cli, console
from cortex.services.github_agent_demo import build_github_agent_payload, run_github_agent_demo
from cortex.services.github_agent_session import GitHubAgentSession


@cli.group("agent")
def agent_cmds() -> None:
    """Declarative YAML agent interface for CORTEX."""


@agent_cmds.command("init")
@click.option(
    "--output",
    "-o",
    default="role.yaml",
    help="Output path for the scaffold.",
)
def agent_init(output: str) -> None:
    """Generate a scaffold role.yaml with sensible defaults."""
    from cortex.extensions.agent.schema import AgentRole

    scaffold = AgentRole.scaffold()
    path = Path(output)
    path.write_text(scaffold.to_yaml(), encoding="utf-8")
    console.print(f"[green]✅ Scaffold written to {path}[/green]")


@agent_cmds.command("validate")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to role.yaml.",
)
def agent_validate(config: str) -> None:
    """Validate a role.yaml configuration file."""
    from cortex.extensions.agent.schema import AgentRole

    try:
        role = AgentRole.from_yaml_file(config)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        sys.exit(1)

    table = Table(title=f"Agent: {role.name}", show_lines=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Model", role.model)
    table.add_row("Tenant", role.tenant_id)
    table.add_row("Project", role.project_id)
    table.add_row("L1 Tokens", str(role.memory.working_memory_tokens))
    table.add_row("Session Budget", str(role.guardrails.max_session_tokens))
    table.add_row("ART ρ", f"{role.memory.art_rho:.2f}")
    table.add_row("Pruning Threshold", f"{role.memory.pruning_threshold:.2f}")
    table.add_row("Retrieval Band", role.memory.retrieval_band)
    table.add_row("Sparse Encoding", str(role.memory.sparse_encoding))
    table.add_row("Silent Engrams", str(role.memory.silent_engrams))
    table.add_row("Tools", ", ".join(role.tools) or "none")

    console.print(table)
    console.print("[green]✅ Configuration valid[/green]")


def _run_interactive_agent_loop(agent) -> None:
    """Run the interactive loop for an agent."""
    console.print(f"[bold cyan]🧠 Agent '{agent.name}' active (model={agent.model})[/bold cyan]")
    console.print(
        f"[dim]Budget: {agent.guardrail.max_tokens} tokens | "
        f"L1: {agent.working_memory.max_tokens} tokens[/dim]"
    )
    console.print("[dim]Type 'exit' or Ctrl+C to quit.[/dim]\n")

    try:
        while True:
            try:
                user_input = console.input("[bold green]> [/bold green]")
            except EOFError:
                break

            if user_input.strip().lower() in ("exit", "quit", "q"):
                break

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            estimated_tokens = max(1, len(user_input) // 4)

            if not agent.guardrail.consume(estimated_tokens):
                console.print("[red]⛔ Session budget exhausted. Agent terminated.[/red]")
                break

            agent.guardrail.tick_turn()

            # Echo status (placeholder for actual LLM call)
            console.print(
                f"[dim](tokens: {agent.guardrail.consumed}/"
                f"{agent.guardrail.max_tokens}, "
                f"turn: {agent.guardrail.turns})[/dim]"
            )
            console.print(f"[yellow]🤖 [{agent.model}] Processing: {user_input[:80]}...[/yellow]\n")

    except KeyboardInterrupt:
        console.print("\n[dim]Agent session ended.[/dim]")

    # Final status
    console.print_json(json.dumps(agent.guardrail.status(), indent=2))


@agent_cmds.command("run")
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Path to role.yaml.",
)
@click.option("--dry-run", is_flag=True, help="Compile but don't execute.")
def agent_run(config: str, dry_run: bool) -> None:
    """Compile and run an agent from a YAML role definition."""
    from cortex.extensions.agent.loader import load_agent

    try:
        agent = load_agent(config)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]❌ Failed to compile agent: {e}[/red]")
        sys.exit(1)

    if dry_run:
        console.print(f"[green]✅ Agent '{agent.name}' compiled successfully (dry-run)[/green]")
        console.print_json(json.dumps(agent.status(), indent=2))
        return

    _run_interactive_agent_loop(agent)


def _emit_json_result(payload: dict[str, object]) -> None:
    console.print_json(data=payload)


def _coerce_repl_value(raw: str) -> object:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        return raw


def _parse_github_repl_line(line: str) -> dict[str, object]:
    stripped = line.strip()
    if not stripped:
        raise ValueError("empty input")
    if stripped.startswith("{"):
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")
        if "op" not in payload:
            raise ValueError("JSON payload must include `op`.")
        return payload

    tokens = shlex.split(stripped)
    if not tokens:
        raise ValueError("empty input")

    op = tokens[0]
    kwargs: dict[str, object] = {}
    for token in tokens[1:]:
        if "=" not in token:
            raise ValueError("Use `key=value` pairs or a JSON object.")
        key, value = token.split("=", 1)
        kwargs[key.replace("-", "_")] = _coerce_repl_value(value)

    remote = kwargs.pop("remote", "origin")
    return build_github_agent_payload(op=op, remote=str(remote), **kwargs)


@agent_cmds.command("github")
@click.option("--op", default="status", show_default=True, help="GitHubAgent operation.")
@click.option("--remote", default="origin", show_default=True, help="Git remote to resolve.")
@click.option("--path", default=None, help="Repo-relative path for file-oriented ops.")
@click.option("--lines", default=None, help="Line selection, e.g. `10` or `10-25`.")
@click.option("--query", default=None, help="Search query for the search op.")
@click.option("--language", default=None, help="Language qualifier for search.")
@click.option("--symbol", default=None, help="Symbol qualifier for search.")
@click.option("--all-repos", is_flag=True, help="Disable repo: scoping in search.")
@click.option("--pr-number", type=int, default=None, help="Pull request number.")
@click.option("--commit-sha", default=None, help="Commit SHA for diff_url.")
@click.option("--format-name", default=None, help="Format for diff_url, usually patch or diff.")
@click.option("--ref", "git_ref", default=None, help="Git ref for blame/history.")
@click.option("--title", default=None, help="PR title for pr_create.")
@click.option("--body", default=None, help="PR body for pr_create.")
@click.option("--base", default=None, help="Base branch for pr_create.")
@click.option("--head", default=None, help="Head branch for pr_create.")
@click.option("--draft", is_flag=True, help="Create a draft PR.")
@click.option("--fill", is_flag=True, help="Ask gh to fill title/body from commits.")
@click.option("--web", is_flag=True, help="Open browser flow for supported gh ops.")
@click.option("--name-with-owner", default=None, help="owner/repo identifier for repo_clone.")
@click.option("--directory", default=None, help="Destination directory for repo_clone.")
@click.option("--timeout", default=5.0, type=float, show_default=True, help="Wait time in seconds.")
def agent_github(
    op: str,
    remote: str,
    path: str | None,
    lines: str | None,
    query: str | None,
    language: str | None,
    symbol: str | None,
    all_repos: bool,
    pr_number: int | None,
    commit_sha: str | None,
    format_name: str | None,
    git_ref: str | None,
    title: str | None,
    body: str | None,
    base: str | None,
    head: str | None,
    draft: bool,
    fill: bool,
    web: bool,
    name_with_owner: str | None,
    directory: str | None,
    timeout: float,
) -> None:
    """Run the GitHub builtin agent once and print the JSON reply."""
    payload = build_github_agent_payload(
        op=op,
        remote=remote,
        path=path,
        lines=lines,
        query=query,
        language=language,
        symbol=symbol,
        all_repos=all_repos,
        pr_number=pr_number,
        commit_sha=commit_sha,
        format_name=format_name,
        ref=git_ref,
        title=title,
        body=body,
        base=base,
        head=head,
        draft=draft,
        fill=fill,
        web=web,
        name_with_owner=name_with_owner,
        directory=directory,
    )
    result = _run_async(run_github_agent_demo(payload, timeout=timeout))
    _emit_json_result(result)
    if "error" in result:
        raise SystemExit(1)


@agent_cmds.command("github-repl")
@click.option("--timeout", default=5.0, type=float, show_default=True, help="Reply wait timeout.")
def agent_github_repl(timeout: float) -> None:
    """Open an interactive REPL backed by the GitHub builtin agent."""

    async def _repl() -> None:
        console.print("[bold cyan]CORTEX GITHUB REPL[/bold cyan]")
        console.print("[dim]Examples:[/dim]")
        console.print("[dim]  status[/dim]")
        console.print("[dim]  permalink path=cortex/cli/github_cmds.py lines=10-25[/dim]")
        console.print('[dim]  {"op":"search","query":"store_fact","path":"cortex/engine"}[/dim]')
        console.print("[dim]Type `exit` or `quit` to leave.[/dim]\n")

        async with GitHubAgentSession(caller_id="agent-github-repl") as session:
            while True:
                try:
                    line = await asyncio.to_thread(console.input, "[bold green]github> [/bold green]")
                except (EOFError, KeyboardInterrupt):
                    console.print()
                    break

                if line.strip().lower() in {"exit", "quit", "q"}:
                    break
                if not line.strip():
                    continue

                try:
                    payload = _parse_github_repl_line(line)
                    result = await session.request(payload, timeout=timeout)
                    _emit_json_result(result)
                except (json.JSONDecodeError, ValueError) as err:
                    console.print(f"[red]{err}[/red]")

    asyncio.run(_repl())
