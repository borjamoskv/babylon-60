#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
CORTEX — SWARM DASHBOARD (VOID-BEYOND).

Real-time TUI for monitoring the Legion 10,000 swarm.
Visualizes reputation slashing, consensus alignment, and exergy extraction.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from cortex.core.paths import resolve_native_binary

# Configuración de Rutas (Ω₀)
CORTEX_DB_BIN = resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN")


def _resolve_db_path() -> Path:
    """Resolve the dashboard DB path with the documented env precedence."""
    override = os.environ.get("CORTEX_DB_PATH") or os.environ.get("CORTEX_DB")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cortex" / "cortex.db"


# Backward-compatible DB alias used by entrypoint/tests that verify env precedence.
DB_PATH = _resolve_db_path()

def get_native_events(role: str | None = None, limit: int = 5):
    """Fetches real-time events from the native silicon ledger."""
    if CORTEX_DB_BIN is None:
        return []
    try:
        cmd = [str(CORTEX_DB_BIN), "query", role if role else "all", str(limit)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return []

async def get_swarm_telemetry():
    """Simulates or fetches density report from the active commander."""
    # En un entorno real, interrogaríamos al bus compartido
    return {
        "legions": 5,
        "centurions": 12,
        "agents": 120,
        "shards": 4,
        "exergy": 0.94,
        "thermal_status": "STABLE"
    }


def make_grid(agents):
    """Generates the 10x10 visual grid."""
    grid_table = Table.grid(expand=True)
    for _ in range(10):
        grid_table.add_column(justify="center")

    for i in range(0, 100, 10):
        row_cells = []
        for j in range(10):
            idx = i + j
            if idx < len(agents):
                rep = agents[idx]["reputation_score"]
                if rep > 0.9:
                    char = "[bold green]💎[/]"
                elif rep > 0.5:
                    char = "[yellow]⚪[/]"
                else:
                    char = "[bold red]💀[/]"
                row_cells.append(char)
            else:
                row_cells.append("[dim]◌[/]")
        grid_table.add_row(*row_cells)
    return grid_table


def make_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="grid", ratio=2),
        Layout(name="stats", ratio=1),
    )
    return layout


async def main():
    layout = make_layout()
    layout["main"].split_column(
        Layout(name="top"),
        Layout(name="findings", size=10)
    )
    layout["top"].split_row(
        Layout(name="grid", ratio=2),
        Layout(name="stats", ratio=1),
    )

    with Live(layout, refresh_per_second=2, screen=True):
        while True:
            # 1. Fetch Data
            bounties = get_native_events("BOUNTY", limit=5)
            all_events = get_native_events(limit=20)
            telemetry = await get_swarm_telemetry()
            
            # 2. Update Header
            status_color = "green" if telemetry["thermal_status"] == "STABLE" else "red"
            layout["header"].update(Panel(
                f"[bold #2B3BE5]CORTEX SWARM APEX[/] | "
                f"Status: [{status_color}]{telemetry['thermal_status']}[/] | "
                f"Exergy: [cyan]{telemetry['exergy']*100:.1f}%[/] | "
                f"Nodes: [bold]{telemetry['agents']}[/]",
                border_style="#2B3BE5"
            ))

            # 3. Update Grid (Simulation for visual pulse)
            layout["grid"].update(Panel(
                make_grid([{"reputation_score": 0.95} for _ in range(telemetry["agents"])]),
                title="[bold]Legion Presence (O1 Sharded)[/]",
                border_style="white"
            ))

            # 4. Update Stats
            stats_table = Table(show_header=False, expand=True)
            stats_table.add_row("Legions", str(telemetry["legions"]))
            stats_table.add_row("Centurions", str(telemetry["centurions"]))
            stats_table.add_row("Active Shards", str(telemetry["shards"]))
            stats_table.add_row("Native Events", str(len(all_events)))
            
            layout["stats"].update(Panel(
                stats_table,
                title="[bold]Thermal Telemetry[/]",
                border_style="magenta"
            ))

            # 5. Update Findings
            findings_table = Table(title="[bold yellow]LATEST SWARM FINDINGS (BOUNTY)[/]", expand=True)
            findings_table.add_column("TS", style="dim")
            findings_table.add_column("Agent", style="cyan")
            findings_table.add_column("Target", style="green")
            
            for b in bounties:
                meta = json.loads(b["metadata_json"])
                findings_table.add_row(
                    b["timestamp"].split("T")[1][:8],
                    meta.get("agent", "UNKNOWN"),
                    b["content"].replace("Bounty detected by swarm: ", "")[:50]
                )
            
            layout["findings"].update(findings_table)

            await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
