#!/usr/bin/env python3
"""
CORTEX-SWARM-STRIKE (Ω_3) — Massive Parallel Bounty Extraction.
Deploys a Forensic Legion in Strike Mode to scan for vulnerabilities at scale.
"""

import asyncio
import logging
import time
from pathlib import Path
import json

from cortex.engine.swarm_10k import SwarmCommander
from cortex.cli import console
from rich.panel import Panel

# Configuración de Logging CORTEX
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.swarm.strike")

DEFAULT_TARGETS = [
    {"domain": "forensic", "url": "https://github.com/borjamoskv/Cortex-Persist", "type": "repo"},
    {"domain": "forensic", "url": "https://github.com/borjamoskv/antigravity", "type": "repo"},
    {"domain": "forensic", "url": "core-axiom-check", "type": "internal"}
]

async def run_strike(target_list: list[dict]):
    bus_path = Path("~/.cortex/swarm_bus").expanduser()
    bus_path.mkdir(parents=True, exist_ok=True)
    
    commander = SwarmCommander(bus_path=bus_path)
    await commander.initialize()
    
    console.print(
        Panel(
            "🔱 [bold #2B3BE5]LEGION-STRIKE ACTIVATED[/]\n"
            "Mode: [bold red]STRIKE (Overclocked)[/]\n"
            f"Targets: [cyan]{len(target_list)}[/]\n"
            "Protection: [dim]Native Arbiter Ω0 Enabled[/]",
            border_style="#2B3BE5",
        )
    )

    start_time = time.perf_counter()
    
    # Entramos en modo STRIKE para saltar las restricciones térmicas (Ω2)
    async with commander.strike_mode("forensic") as legion:
        console.print(f"[bold yellow]⚡ Thermal Gates BYPASSED for {legion.id}[/]")
        
        # Dispatch masivo de tareas
        tasks = []
        for t in target_list:
            # Transformamos el target al formato de tarea del enjambre
            task = {
                "id": f"strike-{int(time.time())}-{hash(t['url']) % 1000}",
                "domain": t["domain"],
                "target": t["url"],
                "action": "vulnerability_scan",
                "vessel_spec": "bounty-striker-v2"
            }
            tasks.append(task)
            
        await commander.execute_global_dispatch(tasks, parallel=True)

    # Reporte de Densidad
    report = await commander.get_density_report()
    elapsed = time.perf_counter() - start_time
    
    console.print("\n[bold #2B3BE5]💎 STRIKE CRYSTALLIZATION COMPLETE[/]")
    console.print(f"  [bold]Time:[/] {elapsed:.2f}s")
    console.print(f"  [bold]Legions:[/] {report['legions']}")
    console.print(f"  [bold]Centurions:[/] {report['centurions']}")
    console.print(f"  [bold]Active Agents:[/] {report['agents']}")
    
    await commander.consolidate_and_annihilate()

if __name__ == "__main__":
    try:
        asyncio.run(run_strike(DEFAULT_TARGETS))
    except KeyboardInterrupt:
        console.print("\n[red]Strike Aborted.[/]")
