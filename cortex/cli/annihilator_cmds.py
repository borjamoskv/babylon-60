"""CORTEX Annihilator CLI Commands.

Manual trigger for the C5-REAL Purge Daemon.
"""

from __future__ import annotations

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, _run_async, cli
from cortex.daemon.annihilator import AnnihilatorDaemon

console = Console()


async def _run_annihilate(db_path: str) -> None:
    console.print("[bold red]⧖ INITIATING C5-REAL ANNIHILATION PROTOCOL[/]")
    daemon = AnnihilatorDaemon(db_path=db_path)
    entropy = await daemon.measure_entropy()

    console.print(f"Current Entropy Approximation: {entropy:.2f}")

    # We force the purge for manual testing
    results = await daemon.purge()

    if "error" in results:
        console.print(f"[bold red]✗ ANNIHILATION FAILED: {results['error']}[/]")
    else:
        console.print("[bold green]✓ STRUCTURAL PURGE COMPLETE (VACUUM EXECUTED).[/]")


@cli.command(name="annihilate")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def annihilate_cmd(db: str) -> None:
    """Manually trigger the Annihilation Protocol."""
    _run_async(_run_annihilate(db))
