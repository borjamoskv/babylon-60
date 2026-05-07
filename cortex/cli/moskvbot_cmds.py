"""CLI commands for MOSKVBot coding missions."""

from __future__ import annotations

import json
from pathlib import Path

import click
import yaml
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import _run_async, cli, console
from cortex.extensions.moskvbot import (
    CloudExecutionUnavailable,
    CommandSpec,
    ExecutionBackend,
    MOSKVBot,
    MOSKVBotPlanner,
    MissionPlan,
    MissionResult,
    WorkerSpec,
)


@cli.group("moskvbot")
def moskvbot_cmds() -> None:
    """MOSKVBot — isolated coding-agent mission runner."""


@moskvbot_cmds.command("init")
@click.option("--output", "-o", default="moskvbot.yaml", help="Output manifest path.")
def init_manifest(output: str) -> None:
    """Write a starter MOSKVBot mission manifest."""
    manifest = {
        "goal": "Implement a focused code change and validate it.",
        "backend": ExecutionBackend.LOCAL_WORKTREE.value,
        "parallelism": 2,
        "keep_worktree": True,
        "commit": False,
        "workers": [
            {
                "worker_id": "executor",
                "role": "coding-worker",
                "objective": "Apply the requested code change.",
                "owns": ["cortex/extensions/moskvbot"],
                "commands": [],
            }
        ],
        "validation_commands": ["git diff --check"],
    }
    path = Path(output)
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    console.print(f"[green]MOSKVBot manifest written to {path}[/green]")


@moskvbot_cmds.command("plan")
@click.argument("goal")
@click.option("--repo", default=".", help="Target Git repository.")
@click.option(
    "--backend",
    type=click.Choice([backend.value for backend in ExecutionBackend]),
    default=ExecutionBackend.LOCAL_WORKTREE.value,
    help="Execution backend.",
)
@click.option(
    "--command",
    "commands",
    multiple=True,
    help="Worker command to include in the plan. May be repeated.",
)
@click.option(
    "--validation-command",
    "validation_commands",
    multiple=True,
    help="Validation command. Defaults to git diff --check.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def plan_cmd(
    goal: str,
    repo: str,
    backend: str,
    commands: tuple[str, ...],
    validation_commands: tuple[str, ...],
    as_json: bool,
) -> None:
    """Create a deterministic coding mission plan."""
    plan = _build_plan(goal, repo, backend, commands, validation_commands)
    if as_json:
        console.print_json(json.dumps(plan.to_dict(), indent=2))
        return
    _render_plan(plan)


@moskvbot_cmds.command("run")
@click.argument("goal")
@click.option("--repo", default=".", help="Target Git repository.")
@click.option(
    "--backend",
    type=click.Choice([backend.value for backend in ExecutionBackend]),
    default=ExecutionBackend.LOCAL_WORKTREE.value,
    help="Execution backend.",
)
@click.option(
    "--command",
    "commands",
    multiple=True,
    help="Worker command to execute in the isolated worktree. May be repeated.",
)
@click.option(
    "--validation-command",
    "validation_commands",
    multiple=True,
    help="Validation command. Defaults to git diff --check.",
)
@click.option("--parallelism", type=int, default=2, show_default=True)
@click.option("--worktree-base", default=None, help="Directory for isolated worktrees.")
@click.option("--keep-worktree/--cleanup-worktree", default=True, show_default=True)
@click.option("--commit", is_flag=True, help="Commit successful mission changes in the worktree.")
@click.option("--commit-message", default=None, help="Git commit message.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def run_cmd(
    goal: str,
    repo: str,
    backend: str,
    commands: tuple[str, ...],
    validation_commands: tuple[str, ...],
    parallelism: int,
    worktree_base: str | None,
    keep_worktree: bool,
    commit: bool,
    commit_message: str | None,
    as_json: bool,
) -> None:
    """Run a MOSKVBot mission in an isolated worktree."""
    plan = _build_plan(goal, repo, backend, commands, validation_commands)
    bot = MOSKVBot(repo)
    try:
        result = _run_async(
            bot.run(
                plan,
                parallelism=parallelism,
                keep_worktree=keep_worktree,
                commit=commit,
                commit_message=commit_message,
                worktree_base_path=worktree_base,
            )
        )
    except CloudExecutionUnavailable as exc:
        raise click.ClickException(str(exc)) from exc

    if as_json:
        console.print_json(json.dumps(result.to_dict(), indent=2))
        return
    _render_result(result)


@moskvbot_cmds.command("status")
@click.option("--repo", default=".", help="Target Git repository.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def status_cmd(repo: str, as_json: bool) -> None:
    """Show MOSKVBot repository capabilities and default checks."""
    planner = MOSKVBotPlanner(repo)
    snapshot = planner.snapshot()
    suggested = planner.suggested_validation_commands(snapshot)
    payload = {
        "repo": snapshot.to_dict(),
        "backends": [backend.value for backend in ExecutionBackend],
        "cloud_isolated": "adapter-required",
        "suggested_validation_commands": [command.display for command in suggested],
    }
    if as_json:
        console.print_json(json.dumps(payload, indent=2))
        return

    table = Table(title="MOSKVBot Status", show_lines=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Repo", str(snapshot.repo_path))
    table.add_row("Branch", snapshot.branch)
    table.add_row("HEAD", snapshot.head_sha[:12])
    table.add_row("Dirty files", str(len(snapshot.dirty_files)))
    table.add_row("Languages", ", ".join(f"{k}:{v}" for k, v in snapshot.language_counts.items()))
    table.add_row("Entrypoints", ", ".join(snapshot.entrypoints) or "none")
    table.add_row("Cloud backend", "adapter required")
    table.add_row("Suggested checks", "\n".join(command.display for command in suggested))
    console.print(table)


def _build_plan(
    goal: str,
    repo: str,
    backend: str,
    commands: tuple[str, ...],
    validation_commands: tuple[str, ...],
) -> MissionPlan:
    planner = MOSKVBotPlanner(repo)
    worker_specs = _workers_from_commands(commands)
    validations = (
        tuple(CommandSpec.from_string(command) for command in validation_commands)
        if validation_commands
        else None
    )
    return planner.build(
        goal,
        backend=ExecutionBackend(backend),
        workers=worker_specs,
        validation_commands=validations,
    )


def _workers_from_commands(commands: tuple[str, ...]) -> tuple[WorkerSpec, ...]:
    if not commands:
        return ()
    command_specs = tuple(CommandSpec.from_string(command) for command in commands)
    return (
        WorkerSpec(
            worker_id="executor",
            role="coding-worker",
            objective="Execute requested coding commands inside the isolated worktree.",
            commands=command_specs,
            owns=(),
        ),
    )


def _render_plan(plan: MissionPlan) -> None:
    snapshot = plan.snapshot
    console.print(
        Panel(
            f"[bold]Goal[/]: {plan.goal}\n"
            f"[bold]Mission[/]: {plan.mission_id}\n"
            f"[bold]Backend[/]: {plan.backend.value}\n"
            f"[bold]Branch[/]: {plan.branch_name}\n"
            f"[bold]Repo[/]: {plan.repo_path}",
            title="MOSKVBot Plan",
            border_style="cyan",
        )
    )
    table = Table(title="Codebase Snapshot")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Current branch", snapshot.branch)
    table.add_row("HEAD", snapshot.head_sha[:12])
    table.add_row("Dirty files", str(len(snapshot.dirty_files)))
    table.add_row("Languages", ", ".join(f"{k}:{v}" for k, v in snapshot.language_counts.items()))
    table.add_row("Tests indexed", str(len(snapshot.test_files)))
    table.add_row("Validation", "\n".join(command.display for command in plan.validation_commands))
    console.print(table)


def _render_result(result: MissionResult) -> None:
    border = "green" if result.status.value == "completed" else "red"
    console.print(
        Panel(
            f"[bold]Status[/]: {result.status.value}\n"
            f"[bold]Branch[/]: {result.branch_name}\n"
            f"[bold]Worktree[/]: {result.worktree_path or 'cleaned up'}\n"
            f"[bold]Commit[/]: {result.commit_sha or 'none'}\n"
            f"[bold]Changed files[/]: {len(result.changed_files)}",
            title="MOSKVBot Result",
            border_style=border,
        )
    )
    for error in result.errors:
        console.print(f"[red]{error}[/red]")


def main() -> None:
    """Standalone entry point for the moskvbot console script."""
    moskvbot_cmds()
