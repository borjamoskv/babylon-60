"""
pipeline_cmds.py — cortex pipeline <cmd>

CLI surface for the PipelineKernelAgent (Fontanero-Ω).
Auto-discovered by cortex.cli.main via the *_cmds.py convention.

Commands:
  cortex pipeline build   — forge a new pipeline
  cortex pipeline audit   — thermal audit of an existing pipeline
  cortex pipeline unclog  — alias for audit (Fontanero terminology)
  cortex pipeline run     — run a unix/ci-cd pipeline directly (no bus)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.common import cli

console = Console()

# ─── Group ───────────────────────────────────────────────────────────────────


@click.group("pipeline")
def pipeline_cmds() -> None:
    """Fontanero-Ω: Sovereign Pipeline Kernel — build, audit, repair."""


cli.add_command(pipeline_cmds)


# ─── BUILD ───────────────────────────────────────────────────────────────────


@pipeline_cmds.command("build")
@click.option("--id", "pipeline_id", required=True, help="Pipeline identifier.")
@click.option(
    "--kind",
    type=click.Choice(["unix_pipe", "asyncio_stream", "sse_feed", "ci_cd_workflow"]),
    default="unix_pipe",
    show_default=True,
    help="Pipeline type.",
)
@click.option("--source", default="", help="Source endpoint / command.")
@click.option("--dest", default="", help="Destination endpoint / command.")
@click.option(
    "--step",
    "steps",
    multiple=True,
    help="Pipeline step (repeatable). E.g. --step 'cat file' --step 'grep foo'",
)
@click.option("--timeout", default=30.0, show_default=True, help="Timeout in seconds.")
@click.option("--dry-run", is_flag=True, help="Print spec without executing.")
def build(
    pipeline_id: str,
    kind: str,
    source: str,
    dest: str,
    steps: tuple[str, ...],
    timeout: float,
    dry_run: bool,
) -> None:
    """Forge a new execution pipeline."""
    from cortex.agents.builtins.pipeline_kernel_agent import (
        PipelineSpec,
        PipelineTelemetry,
        PipelineType,
        _run_ci_cd_workflow,
        _run_unix_pipe,
    )

    spec = PipelineSpec(
        pipeline_id=pipeline_id,
        kind=PipelineType(kind),
        source=source,
        destination=dest,
        steps=list(steps),
        timeout_s=timeout,
    )

    if dry_run:
        _show_spec(spec)
        return

    if not steps and not (source and dest):
        console.print("[red]✗ Provide --step(s) or both --source and --dest[/red]")
        raise click.Abort()

    _show_spec(spec)

    telemetry = PipelineTelemetry(
        pipeline_id=pipeline_id,
        kind=kind,
        started_at=time.monotonic(),
    )

    async def _run() -> Any:
        if spec.kind == PipelineType.UNIX_PIPE:
            return await _run_unix_pipe(spec, telemetry)
        elif spec.kind == PipelineType.CI_CD_WORKFLOW:
            return await _run_ci_cd_workflow(spec, telemetry)
        else:
            telemetry.finalize()
            return f"Type '{kind}' requires bus dispatch (no direct CLI runner)."

    result = asyncio.run(_run())
    _show_result(telemetry, result)


# ─── AUDIT / UNCLOG ──────────────────────────────────────────────────────────


@pipeline_cmds.command("audit")
@click.argument("pipeline_id")
def audit(pipeline_id: str) -> None:
    """Thermal audit of an existing pipeline (zombie detection, open FDs)."""
    from cortex.agents.builtins.pipeline_kernel_agent import audit_pipeline

    console.print(f"[bold cyan]🔬 Auditing pipeline:[/] {pipeline_id}")
    result = asyncio.run(audit_pipeline(pipeline_id))
    _show_audit(result)


@pipeline_cmds.command("unclog")
@click.argument("pipeline_id")
def unclog(pipeline_id: str) -> None:
    """Alias for audit (Fontanero-Ω /fontanero-unclog)."""
    from cortex.agents.builtins.pipeline_kernel_agent import audit_pipeline

    console.print(f"[bold yellow]🔧 Unclogging pipeline:[/] {pipeline_id}")
    result = asyncio.run(audit_pipeline(pipeline_id))
    _show_audit(result)


# ─── RUN (direct, no bus) ─────────────────────────────────────────────────────


@pipeline_cmds.command("run")
@click.option("--cmd", required=True, help='Shell command to run. Use pipes: "cat f | grep x"')
@click.option("--id", "pipeline_id", default="cli-run", help="Pipeline ID for telemetry.")
@click.option("--timeout", default=30.0, show_default=True)
def run(cmd: str, pipeline_id: str, timeout: float) -> None:
    """Run a unix pipe directly from CLI (C5-REAL, output to stdout)."""
    import asyncio

    from cortex.agents.builtins.pipeline_kernel_agent import (
        PipelineSpec,
        PipelineTelemetry,
        PipelineType,
        _run_unix_pipe,
    )

    spec = PipelineSpec(
        pipeline_id=pipeline_id,
        kind=PipelineType.UNIX_PIPE,
        source="stdin",
        destination="stdout",
        steps=[cmd],
        timeout_s=timeout,
    )
    telemetry = PipelineTelemetry(
        pipeline_id=pipeline_id, kind="unix_pipe", started_at=time.monotonic()
    )
    output = asyncio.run(_run_unix_pipe(spec, telemetry))
    console.print(output)
    _show_telemetry_inline(telemetry)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _show_spec(spec: Any) -> None:
    content = (
        f"[bold]ID:[/]       {spec.pipeline_id}\n"
        f"[bold]Kind:[/]     {spec.kind.value}\n"
        f"[bold]Source:[/]   {spec.source or '—'}\n"
        f"[bold]Dest:[/]     {spec.destination or '—'}\n"
        f"[bold]Steps:[/]    {len(spec.steps)}\n"
        f"[bold]Timeout:[/]  {spec.timeout_s}s\n"
    )
    if spec.steps:
        for i, s in enumerate(spec.steps):
            content += f"  [dim]{i}.[/] {s}\n"
    console.print(Panel(content, title="Pipeline Spec", border_style="cyan", expand=False))


def _show_result(telemetry: Any, result: Any) -> None:
    t = telemetry.as_dict()
    status_color = "green" if t["exit_code"] == 0 else "red"
    verdict = "✓ SUCCESS" if t["exit_code"] == 0 else "✗ FAILED"
    content = (
        f"[{status_color}][bold]{verdict}[/bold][/{status_color}]\n\n"
        f"[bold]Latency:[/]   {t['latency_ms']}ms\n"
        f"[bold]Bytes:[/]     {t['bytes_total']}\n"
        f"[bold]Speed:[/]     {t['bytes_per_second']:.0f} B/s\n"
        f"[bold]Reality:[/]   {t['reality_level']}\n"
    )
    if t.get("error"):
        content += f"[bold red]Error:[/]     {t['error']}\n"
    if isinstance(result, str) and result.strip():
        preview = result[:500]
        content += f"\n[dim]Output preview:[/dim]\n{preview}"
        if len(result) > 500:
            content += f"\n[dim]... ({len(result) - 500} more chars)[/dim]"
    console.print(Panel(content, title="Pipeline Result", border_style="green", expand=False))


def _show_audit(result: dict[str, Any]) -> None:
    verdict = result.get("verdict", "UNKNOWN")
    color = "green" if verdict == "CLEAN" else "yellow"
    content = (
        f"[bold {color}]Verdict: {verdict}[/bold {color}]\n\n"
        f"[bold]Pipeline ID:[/] {result.get('pipeline_id', '?')}\n"
        f"[bold]Open FDs (host):[/] {result.get('open_fds_host', '?')}\n"
        f"[bold]Reality:[/] {result.get('reality_level', '?')}\n"
    )
    zombies = result.get("zombie_processes", [])
    if zombies:
        content += f"\n[bold red]⚠️  Zombie processes ({len(zombies)}):[/bold red]\n"
        for z in zombies[:5]:
            content += f"  [dim]{z}[/dim]\n"
    console.print(Panel(content, title="Pipeline Audit", border_style=color, expand=False))


def _show_telemetry_inline(telemetry: Any) -> None:
    t = telemetry.as_dict()
    console.print(
        f"[dim]Ω₂ telemetry → "
        f"{t['latency_ms']}ms | {t['bytes_total']}B | "
        f"{t['reality_level']}[/dim]"
    )
