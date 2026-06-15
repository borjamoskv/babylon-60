# [C5-REAL] Exergy-Maximized
"""CLI — Replay Commands.

Minimal replay interface for the CORTEX verifiable execution substrate.

Usage:
    cortex replay --trace events.json
    cortex replay --trace events.json --from cortex-runtime-v1
    cortex replay --trace events.json --verify-hash abc123...
    cortex replay --generate-trace --output trace.json
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import cli

logger = logging.getLogger(__name__)
console = Console()


@cli.group("replay")
def replay_group():
    """Replay engine — deterministic trace verification."""


@replay_group.command("run")
@click.option(
    "--trace",
    "-t",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the event trace JSON file.",
)
@click.option(
    "--from",
    "from_hash",
    type=str,
    default=None,
    help="Start replay from a specific hash checkpoint.",
)
@click.option(
    "--verify-hash",
    type=str,
    default=None,
    help="Expected final hash to verify against.",
)
@click.option(
    "--runs",
    "-n",
    type=int,
    default=1,
    help="Number of replay runs for determinism verification (default: 1).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed replay output.",
)
def replay_run(
    trace: Path,
    from_hash: str | None,
    verify_hash: str | None,
    runs: int,
    verbose: bool,
):
    """Replay an event trace and verify determinism.

    Examples:
        cortex replay run --trace events.json
        cortex replay run --trace events.json --runs 3
        cortex replay run --trace events.json --verify-hash abc123...
    """
    from cortex.runtime.event_schema import load_trace
    from cortex.runtime.replay import ReplayEngine

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    # Load trace
    try:
        events = load_trace(trace)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        console.print(f"[bold red]✗ Failed to load trace:[/] {exc}")
        sys.exit(1)

    console.print(
        Panel(
            f"[white]Events: {len(events)} | From: {from_hash or 'genesis'} | Runs: {runs}[/]",
            title="[bold cyan]⟳ CORTEX Replay Engine[/]",
            border_style="bright_blue",
        )
    )

    engine = ReplayEngine()

    if runs > 1:
        # Determinism verification mode
        is_deterministic = engine.verify_determinism(events, runs=runs)
        if is_deterministic:
            console.print("[bold green]✓ DETERMINISM PROVEN[/] — all runs converged")
            sys.exit(0)
        else:
            console.print("[bold red]✗ DETERMINISM VIOLATION[/] — hashes diverged")
            sys.exit(1)

    # Single run
    if from_hash:
        result = engine.replay_from_hash(
            events, start_hash=from_hash, expected_final_hash=verify_hash
        )
    else:
        result = engine.replay(events, expected_final_hash=verify_hash)

    # Output results
    _display_result(result, verify_hash)

    sys.exit(0 if result.success and result.hash_match else 1)


@replay_group.command("generate-trace")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("trace.json"),
    help="Output path for the generated trace (default: trace.json).",
)
@click.option(
    "--tag",
    type=str,
    default="",
    help="Git tag or checkpoint to record in the trace metadata.",
)
def replay_generate_trace(output: Path, tag: str):
    """Generate a canonical event trace from a fixed sequence.

    Useful for creating baseline traces for regression testing.

    Example:
        cortex replay generate-trace --output baseline.json --tag cortex-runtime-v1
    """
    from cortex.runtime.event_schema import save_trace
    from cortex.runtime.system_state import SystemStateVector

    # Canonical trace (same as test suite)
    canonical = [
        {
            "event_type": "agent.registered",
            "source": "agent:health-monitor",
            "payload": {"agent_id": "health-monitor"},
        },
        {
            "event_type": "agent.registered",
            "source": "agent:task-worker",
            "payload": {"agent_id": "task-worker"},
        },
        {"event_type": "agent.started", "source": "agent:health-monitor", "payload": {}},
        {"event_type": "agent.started", "source": "agent:task-worker", "payload": {}},
        {
            "event_type": "task.submitted",
            "source": "system",
            "payload": {"task_id": "t-001", "description": "determinism proof"},
        },
        {
            "event_type": "task.completed",
            "source": "agent:task-worker",
            "payload": {"task_id": "t-001", "result": "ok"},
        },
        {
            "event_type": "system.error",
            "source": "agent:health-monitor",
            "payload": {"error": "synthetic-fault"},
        },
        {"event_type": "system.recovery", "source": "system", "payload": {}},
        {
            "event_type": "task.submitted",
            "source": "system",
            "payload": {"task_id": "t-002", "description": "post-recovery task"},
        },
        {
            "event_type": "task.completed",
            "source": "agent:task-worker",
            "payload": {"task_id": "t-002", "result": "ok"},
        },
        {"event_type": "agent.stopped", "source": "agent:task-worker", "payload": {}},
        {"event_type": "agent.stopped", "source": "agent:health-monitor", "payload": {}},
    ]

    sv = SystemStateVector()
    for entry in canonical:
        sv.apply(
            event_type=entry["event_type"],
            source=entry["source"],
            payload=entry.get("payload", {}),
        )

    saved = save_trace(sv, output, source_tag=tag)
    console.print(f"[bold green]✓ Trace saved:[/] {saved}")
    console.print(f"  Events: {sv.tick} | Final hash: {sv.hash[:24]}...")


@replay_group.command("schema")
def replay_schema():
    """Print the canonical event trace JSON schema."""
    from cortex.runtime.event_schema import EVENT_JSON_SCHEMA

    console.print_json(json.dumps(EVENT_JSON_SCHEMA, indent=2))


def _display_result(result, verify_hash: str | None):
    """Rich display of a ReplayResult."""
    table = Table(title="Replay Result", border_style="bright_blue")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Success", "✓" if result.success else "✗")
    table.add_row("Ticks Replayed", str(result.ticks_replayed))
    table.add_row("Final Hash", result.final_hash[:32] + "...")
    table.add_row("Hash Match", "✓" if result.hash_match else "✗")

    if result.divergence_tick is not None:
        table.add_row("Divergence Tick", f"[bold red]{result.divergence_tick}[/]")

    if verify_hash:
        table.add_row("Expected Hash", verify_hash[:32] + "...")

    if result.errors:
        table.add_row("Errors", f"[bold red]{len(result.errors)}[/]")
        for err in result.errors[:5]:
            table.add_row("", f"[dim red]{err}[/]")

    console.print(table)

    # Snapshot summary
    snap = result.final_snapshot
    if snap:
        snap_table = Table(title="Final State Snapshot", border_style="dim")
        snap_table.add_column("Metric", style="cyan")
        snap_table.add_column("Value", style="white")
        for key in ["tick", "entropy", "exergy", "phase", "tasks_completed", "tasks_failed"]:
            if key in snap:
                snap_table.add_row(key, str(snap[key]))
        console.print(snap_table)
