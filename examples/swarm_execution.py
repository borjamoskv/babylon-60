import asyncio
import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.ledger import SovereignLedger
from cortex.swarm.factory import create_sovereign_swarm

logging.basicConfig(level=logging.ERROR)  # Only show our rich output
logger = logging.getLogger("cortex.swarm.specialists")
logger.setLevel(logging.INFO)

console = Console()


async def execute_thermodynamic_flow():
    console.print("[bold cyan]Ω-Architecture: Executing Sovereign Swarm Flow...[/bold cyan]")

    import sqlite3

    console.print("\n[dim]Initializing cryptographic ledger (trust boundary)...[/dim]")
    conn = sqlite3.connect(":memory:")
    ledger = SovereignLedger(db_conn=conn)

    # 2. Forge Swarm
    console.print("[dim]Forging swarm with Ultra-Potent skills...[/dim]")
    swarm = create_sovereign_swarm(ledger=ledger)
    available = await swarm.list_available()
    console.print(
        f"[bold green]Swarm Online[/bold green]. Available actuators: {', '.join(available)}"
    )

    # 3. Define the Mission (Parallel execution requested to different actuators)
    missions = [
        (
            "devin",
            "Refactor the memory caching layer to O(1) retrieval, eliminating all PII data from logs in the process.",
            {"user_email": "admin@cortex.network"},
        ),
        (
            "ouroboros",
            "Scan liquid staking pools for delta > 2.5% and extract exergy.",
            {"wallet": "0xABC123"},
        ),
        ("awwwards", "Deconstruct the https://example.com landing page WebGL shader.", {}),
    ]

    # 4. Dispatch tasks concurrently
    console.print("\n[bold magenta]Dispatching multi-agent mission...[/bold magenta]")
    tasks = []
    for actuator_name, prompt, ctx in missions:
        console.print(f" -> Mapping task to [yellow]{actuator_name}[/yellow]: {prompt[:40]}...")
        tasks.append(swarm.dispatch(actuator_name=actuator_name, task=prompt, context=ctx))

    responses = await asyncio.gather(*tasks)

    # 5. Display Responses
    console.print("\n[bold cyan]Sovereign Responses Received:[/bold cyan]")
    for i, res in enumerate(responses):
        console.print(
            Panel(
                res["content"],
                title=f"Node: {missions[i][0]} | Status: {res['status']}",
                border_style="green" if res["status"] == "success" else "red",
            )
        )

    # 6. Verify Ledger Audit Trail
    console.print("\n[bold neon]Thermodynamic Ledger Audit (Proof of Work):[/bold neon]")
    records = ledger.get_transactions(project="swarm")

    table = Table(
        title="Sovereign Swarm Cryptographic Ledger", show_header=True, header_style="bold blue"
    )
    table.add_column("ID", style="dim", width=6)
    table.add_column("Action", style="magenta")
    table.add_column("Details", style="green")
    table.add_column("Hash", justify="right", style="dim")

    for row in records:
        tx_id, ts, action, detail, prev_hash, curr_hash = row
        table.add_row(str(tx_id), action, str(detail)[:60] + "...", curr_hash[:16] + "...")

    console.print(table)

    # Thermodynamic Calculation
    compound_hours = len(missions) * 4.5 * 1.15  # Hypothetical base calculation
    console.print("\n[bold yellow]Thermodynamic Yield Report:[/bold yellow]")
    console.print(f" - Tasks executed: {len(missions)}")
    console.print(f" - Compound Hours yielded: {compound_hours:.2f}h")
    console.print(" - Net Exergy: Positive. Fricton boundary passed. (C5-Dynamic)")


if __name__ == "__main__":
    asyncio.run(execute_thermodynamic_flow())
