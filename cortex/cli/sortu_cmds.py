"""CORTEX v12.2 — SORTU-Ω CLI.

Sovereign CLI wrapper for the 10-step Sortu Forge pipeline.
Dynamically maps to the Antigravity Skill directory.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from cortex.cli.common import cli
from cortex.core.paths import resolve_skill_dir, resolve_skill_scripts_dir

logger = logging.getLogger("cortex.cli.sortu")
console = Console()

# Inject SORTU path so the CORTEX environment can find it.
SORTU_SKILL_DIR = resolve_skill_dir("Sortu")
SORTU_SCRIPTS_DIR = resolve_skill_scripts_dir("Sortu")
LOCAL_SORTU_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "sortu"
_SORTU_IMPORT_PATHS = (LOCAL_SORTU_SCRIPTS, SORTU_SCRIPTS_DIR, SORTU_SKILL_DIR)

# Prefer the tracked repo copy first so tests and local development do not
# accidentally import a stale host Sortu implementation from ~/.gemini.
for path in _SORTU_IMPORT_PATHS:
    path_str = str(path)
    while path_str in sys.path:
        sys.path.remove(path_str)

for path in reversed(_SORTU_IMPORT_PATHS):
    if path.exists():
        sys.path.insert(0, str(path))


@click.group("sortu")
def sortu_cmds() -> None:
    """SORTU-Ω Forge Engine — cortex sortu <subcommand>."""


@sortu_cmds.command("forge")
@click.argument("skill_dir", type=click.Path(exists=True))
@click.option("--intent", default="", help="Initial intent for this skill.")
@click.option("--threshold", default=0.7, help="AST overlaps redundancy threshold.")
@click.option("--db", default="cortex_graph_rag.db", help="GraphStore database path.")
def forge_skill(skill_dir: str, intent: str, threshold: float, db: str) -> None:
    """Run the 10-step SORTU pipeline on a target skill directory."""
    asyncio.run(_run_forge(Path(skill_dir), intent, threshold, db))


async def _run_forge(target: Path, intent: str, threshold: float, db: str) -> None:
    try:
        from sortu_engine import SortuEngine

        from cortex.memory.graph_store import GraphStore
    except ImportError as e:
        console.print(f"[red]Failed to load SORTU meta-engine: {e}[/]")
        return

    skills_root = SORTU_SKILL_DIR.parent if SORTU_SKILL_DIR.exists() else target.parent
    graph = GraphStore(db_path=db)
    await graph.initialize()

    engine = SortuEngine(skills_root=skills_root, graph_store=graph, overlap_threshold=threshold)

    with console.status(f"[noir.violet]Forging [bold]{target.name}[/] with SORTU-Ω v12.2...[/]"):
        record = await engine.forge(target, intent=intent)

    if record.state.value == "ACTIVE":
        console.print(
            f"[[noir.cyber]✓[/]] [bold green]FORGE SUCCESS:[/] "
            f"[bold]{record.skill_name}[/] v{record.version} is now ACTIVE."
        )
    else:
        console.print(
            f"[[red]✗[/]] [bold red]FORGE ABORTED:[/] "
            f"{record.abort_reason.value if record.abort_reason else 'UNKNOWN_FAILURE'}"
        )

    # Show biopsy if available
    if record.biopsy:
        table = Table(title=f"⚡ SORTU Biopsy ({record.skill_name})", header_style="bold cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", justify="right", style="green")

        b = record.biopsy
        table.add_row("Total Invocations", str(b.total_invocations))
        table.add_row("Compound Yield", f"{b.compound_yield:.2f}")
        table.add_row("Entropy Cost", f"{b.entropy_cost:.2f}")
        table.add_row("Net Exergy", f"{b.net_exergy:.2f}")
        table.add_row("Verdict", b.verdict)

        console.print(table)


cli.add_command(sortu_cmds)
