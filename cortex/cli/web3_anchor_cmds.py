"""CORTEX Web3 L2 Anchor CLI Commands.

Manual trigger for the Proof-of-Execution anchoring mechanism.
"""

from __future__ import annotations

import click
from rich.console import Console

from cortex.cli.common import DEFAULT_DB, _run_async, cli
from cortex.ledger.web3_anchor import Web3Anchor

console = Console()
_CYBER = "bold #CCFF00"


async def _run_anchor(db_path: str) -> None:
    console.print(f"[{_CYBER}]⧖ INITIATING PROOF-OF-EXECUTION L2 ANCHOR[/]")
    anchor = Web3Anchor(db_path=db_path)

    result = await anchor.anchor_to_l2()

    if result["status"] == "SUCCESS":
        console.print("[bold green]✓ ANCHOR SUCCESSFUL[/]")
        console.print(f"[dim]Mode:[/] {result['mode']}")
        console.print(f"[dim]Network:[/] {result['network']}")
        console.print(f"[dim]Merkle Root:[/] {result['merkle_root']}")
        if result["tx_hash"]:
            console.print(f"[dim]TX Hash:[/] {result['tx_hash']}")
    else:
        console.print(f"[bold red]✗ ANCHOR FAILED: {result.get('error', 'Unknown Error')}[/]")


@cli.command(name="anchor")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def anchor_cmd(db: str) -> None:
    """Manually anchor the Sovereign Ledger to a Web3 L2 network."""
    _run_async(_run_anchor(db))
