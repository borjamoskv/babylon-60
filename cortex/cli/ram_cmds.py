"""
ram_cmds.py — cortex ram <cmd>

CLI surface for the RamAgent (Sovereign RAM Monitor).
Auto-discovered by cortex.cli.main via the *_cmds.py convention.

Commands:
  cortex ram snapshot  — current RAM state (C5-REAL)
  cortex ram gc        — force garbage collection
  cortex ram leaks     — top tracemalloc allocators
  cortex ram watch     — live monitor (polling)
"""

from __future__ import annotations

import time
from threading import Event
from typing import Any

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import cli

console = Console()
_WATCH_PAUSE = Event()


@click.group("ram")
def ram_cmds() -> None:
    """Sovereign RAM Monitor — C5-REAL memory pressure, GC, leak detection."""


cli.add_command(ram_cmds)


# ─── SNAPSHOT ────────────────────────────────────────────────────────────────


@ram_cmds.command("snapshot")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def snapshot(as_json: bool) -> None:
    """Read current RAM state (C5-REAL)."""
    from cortex.agents.builtins.ram_agent import _read_ram_snapshot
    snap = _read_ram_snapshot()
    if as_json:
        import json
        console.print_json(json.dumps(snap.as_dict()))
        return
    _show_snapshot(snap)


# ─── GC ──────────────────────────────────────────────────────────────────────


@ram_cmds.command("gc")
def force_gc() -> None:
    """Force full garbage collection cycle."""
    from cortex.agents.builtins.ram_agent import _force_gc, _read_ram_snapshot
    before = _read_ram_snapshot()
    t0 = time.monotonic()
    collected = _force_gc()
    elapsed = (time.monotonic() - t0) * 1000
    after = _read_ram_snapshot()

    freed = before.heap_current_mb - after.heap_current_mb
    content = (
        f"[green]✓ GC complete[/green]\n\n"
        f"[bold]Objects collected:[/] {collected}\n"
        f"[bold]Heap before:[/]       {before.heap_current_mb:.2f} MB\n"
        f"[bold]Heap after:[/]        {after.heap_current_mb:.2f} MB\n"
        f"[bold]Freed:[/]             {freed:+.2f} MB\n"
        f"[bold]Duration:[/]          {elapsed:.1f}ms\n"
        f"[bold]Reality:[/]           C5-REAL"
    )
    console.print(Panel(content, title="GC Forced", border_style="green", expand=False))


# ─── LEAKS ───────────────────────────────────────────────────────────────────


@ram_cmds.command("leaks")
@click.option("--top", default=10, show_default=True, help="Top N allocators.")
@click.option("--enable-trace", is_flag=True, help="Start tracemalloc if not running.")
def leaks(top: int, enable_trace: bool) -> None:
    """Show top memory allocators via tracemalloc."""
    import tracemalloc

    from cortex.agents.builtins.ram_agent import _top_allocators

    if enable_trace and not tracemalloc.is_tracing():
        tracemalloc.start(25)
        console.print("[dim]tracemalloc started[/dim]")

    if not tracemalloc.is_tracing():
        console.print(
            "[yellow]⚠️  tracemalloc not active. "
            "Run with --enable-trace or set CORTEX_TRACE_MALLOC=1[/yellow]"
        )
        return

    suspects = _top_allocators(top)
    if not suspects:
        console.print("[green]✓ No allocators found (clean heap)[/green]")
        return

    table = Table(title=f"Top {top} Allocators", border_style="cyan")
    table.add_column("File", style="dim", max_width=50)
    table.add_column("Line", justify="right")
    table.add_column("Size (KB)", justify="right", style="yellow")
    table.add_column("Count", justify="right")

    for s in suspects:
        table.add_row(
            s.filename.replace(str(__file__).split("cortex")[0], ""),
            str(s.lineno),
            f"{s.size_kb:.1f}",
            str(s.count),
        )
    console.print(table)


# ─── WATCH ───────────────────────────────────────────────────────────────────


@ram_cmds.command("watch")
@click.option("--interval", default=2.0, show_default=True, help="Poll interval (s).")
@click.option("--cycles", default=0, help="Max cycles (0 = infinite).")
def watch(interval: float, cycles: int) -> None:
    """Live RAM monitor. Ctrl+C to stop."""
    from cortex.agents.builtins.ram_agent import _read_ram_snapshot

    def _render(snap: object) -> Panel:
        return _build_live_panel(snap)

    snap = _read_ram_snapshot()
    cycle = 0
    with Live(_render(snap), refresh_per_second=4, console=console) as live:
        try:
            while True:
                _WATCH_PAUSE.wait(interval)
                snap = _read_ram_snapshot()
                live.update(_render(snap))
                cycle += 1
                if cycles and cycle >= cycles:
                    break
        except KeyboardInterrupt:
            pass
    console.print("[dim]watch stopped[/dim]")


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _status_color(status: str) -> str:
    return {"OK": "green", "WARN": "yellow", "CRITICAL": "red"}.get(status, "white")


def _show_snapshot(snap: Any) -> None:
    d = snap.as_dict()
    color = _status_color(d["status"])
    content = (
        f"[bold {color}]Status: {d['status']}[/bold {color}]\n\n"
        f"[bold]System RAM[/bold]\n"
        f"  Total:    {d['sys_total_mb']:.0f} MB\n"
        f"  Used:     {d['sys_used_mb']:.0f} MB  ({d['sys_pct']}%)\n"
        f"  Free:     {d['sys_free_mb']:.0f} MB\n\n"
        f"[bold]Process (this PID)[/bold]\n"
        f"  RSS:      {d['proc_rss_mb']:.1f} MB\n"
        f"  VMS:      {d['proc_vms_mb']:.1f} MB\n\n"
        f"[bold]Python Heap[/bold]\n"
        f"  Current:  {d['heap_current_mb']:.2f} MB\n"
        f"  Peak:     {d['heap_peak_mb']:.2f} MB\n\n"
        f"[bold]GC Counts:[/bold] gen0={d['gc_counts'][0]} "
        f"gen1={d['gc_counts'][1]} gen2={d['gc_counts'][2]}\n"
        f"[bold]Reality:[/bold] {d['reality_level']}"
    )
    console.print(Panel(content, title="RAM Snapshot", border_style=color, expand=False))


def _build_live_panel(snap: Any) -> Panel:
    d = snap.as_dict()
    color = _status_color(d["status"])
    bar_used = int(d["sys_pct"] / 5)
    bar = "█" * bar_used + "░" * (20 - bar_used)
    content = (
        f"[bold {color}]{d['status']}[/bold {color}]  "
        f"[{color}]{bar}[/{color}] {d['sys_pct']}%\n\n"
        f"Sys: {d['sys_used_mb']:.0f}/{d['sys_total_mb']:.0f} MB   "
        f"RSS: {d['proc_rss_mb']:.1f} MB   "
        f"Heap: {d['heap_current_mb']:.2f} MB\n"
        f"GC: {d['gc_counts']}  |  {d['reality_level']}"
    )
    return Panel(
        content,
        title="[bold]cortex ram watch[/bold]",
        border_style=color,
        expand=False,
    )
