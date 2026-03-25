# CORTEX-TAINT: cazarecompensas-agent:ab12cd34:1742878308
"""
CORTEX CLI — Bounty Hunter Commands.

Thin wrapper over SovereignBountyScanner for CLI-driven bounty discovery.
Business logic lives in cortex.swarm.bounty_scanner and cortex.services.bounty_service.
"""
from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group(name="bounty")
def bounty_cmds():
    """💎 Sovereign Bounty Hunter — multi-platform capital discovery."""
    pass


@bounty_cmds.command("scan")
@click.option("--platform", "-p", type=click.Choice(
    ["all", "algora", "polar", "immunefi", "github"], case_sensitive=False,
), default="all", help="Platform to scan.")
@click.option("--min-reward", "-m", type=float, default=100.0, help="Minimum reward in USD.")
@click.option("--limit", "-l", type=int, default=20, help="Max results per platform.")
@click.option("--persist", is_flag=True, help="Persist accepted leads to CORTEX Ledger.")
def scan_cmd(platform: str, min_reward: float, limit: int, persist: bool) -> None:
    """Scan bounty platforms for high-exergy opportunities."""
    asyncio.run(_run_scan(platform, min_reward, limit, persist))


async def _run_scan(
    platform: str, min_reward: float, limit: int, persist: bool,
) -> None:
    from cortex.swarm.bounty_scanner import (
        AlgoraScanner,
        BountyOpportunity,
        GitHubBountyScanner,
        ImmuneFiScanner,
        PolarScanner,
        SovereignBountyScanner,
    )

    opportunities: list[BountyOpportunity] = []

    if platform == "all":
        scanner = SovereignBountyScanner()
        opportunities = await scanner.scan_all(min_usd=min_reward)
    elif platform == "algora":
        opportunities = await AlgoraScanner().scan(min_usd=min_reward, limit=limit)
    elif platform == "polar":
        opportunities = await PolarScanner().scan(min_usd=min_reward, limit=limit)
    elif platform == "immunefi":
        opportunities = await ImmuneFiScanner().scan(min_usd=min_reward, limit=limit)
    elif platform == "github":
        opportunities = await GitHubBountyScanner().scan(min_usd=min_reward)

    if not opportunities:
        console.print("[yellow]No bounties found above $%.0f threshold.[/yellow]" % min_reward)
        return

    # Display results
    table = Table(title=f"💎 Bounty Scan — {platform.upper()} (min ${min_reward:.0f})")
    table.add_column("#", style="dim", width=3)
    table.add_column("Platform", style="cyan", width=10)
    table.add_column("Reward", style="bold green", justify="right", width=10)
    table.add_column("EV", style="yellow", justify="right", width=10)
    table.add_column("ExRatio", style="magenta", justify="right", width=8)
    table.add_column("C", style="dim", width=3)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Repo", style="dim cyan", max_width=30)

    for i, opp in enumerate(opportunities[:30], 1):
        ev_gate = "✅" if opp.passes_ev_gate() else "❌"
        
        diff_weight = 2 if opp.complexity <= 3 else (5 if opp.complexity <= 6 else 8)
        if opp.complexity > 8: diff_weight = 10
        context_lines = 100 if diff_weight <= 2 else (300 if diff_weight <= 5 else 500)
        entropy_base = diff_weight * 50 + context_lines * 0.1
        ghost_penalty = context_lines * 0.5 if diff_weight >= 5 and opp.reward_usd < 200 else 0
        meta_penalty = (diff_weight ** 2) * 4 if diff_weight >= 8 else 0
        entropy = max(entropy_base + ghost_penalty + meta_penalty, 1.0)
        exergy_ratio = opp.reward_usd / entropy

        table.add_row(
            str(i),
            opp.platform,
            f"${opp.reward_usd:,.0f}",
            f"${opp.ev:,.0f} {ev_gate}",
            f"{exergy_ratio:.2f}",
            str(opp.complexity),
            opp.title[:50],
            opp.repo[:30],
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(opportunities)} opportunities found.[/dim]")

    # Persistence
    if persist:
        try:
            from cortex.cli.common import get_engine
            engine = get_engine()
            await engine.init_db()
            count = 0
            for opp in opportunities:
                if opp.passes_ev_gate():
                    await engine.store(
                        project="cazarecompensas-agent",
                        content=(
                            f"[BountyScan] {opp.platform} | {opp.title}\n"
                            f"Reward: ${opp.reward_usd:.0f} | EV: ${opp.ev:.0f}\n"
                            f"URL: {opp.url}"
                        ),
                        fact_type="scan_lead",
                        tags=["bounty", "scan", opp.platform],
                        confidence="C3",
                        source="cli:bounty_cmds.py",
                        meta={
                            "platform": opp.platform,
                            "reward_usd": opp.reward_usd,
                            "ev": opp.ev,
                            "complexity": opp.complexity,
                            "url": opp.url,
                        },
                    )
                    count += 1
            await engine.close()
            console.print(f"[green]✅ Persisted {count} leads to CORTEX Ledger.[/green]")
        except Exception as e:
            console.print(f"[red]❌ Ledger persistence failed: {e}[/red]")


@bounty_cmds.command("top")
@click.option("--count", "-n", type=int, default=5, help="Number of top bounties to show.")
def top_cmd(count: int) -> None:
    """Show top bounties by Expected Value across all platforms."""
    asyncio.run(_run_top(count))


async def _run_top(count: int) -> None:
    from cortex.swarm.bounty_scanner import SovereignBountyScanner

    scanner = SovereignBountyScanner()
    opportunities = await scanner.scan_all(min_usd=50.0)

    if not opportunities:
        console.print("[yellow]No bounties found.[/yellow]")
        return

    # Sort by EV (already sorted by scan_all, but explicit)
    opportunities.sort(key=lambda o: o.ev, reverse=True)

    console.print(f"\n[bold]🏆 Top {count} Bounties by Expected Value[/bold]\n")
    for i, opp in enumerate(opportunities[:count], 1):
        gate = "[green]PASS[/green]" if opp.passes_ev_gate() else "[red]FAIL[/red]"
        
        diff_weight = 2 if opp.complexity <= 3 else (5 if opp.complexity <= 6 else 8)
        if opp.complexity > 8: diff_weight = 10
        context_lines = 100 if diff_weight <= 2 else (300 if diff_weight <= 5 else 500)
        entropy_base = diff_weight * 50 + context_lines * 0.1
        ghost_penalty = context_lines * 0.5 if diff_weight >= 5 and opp.reward_usd < 200 else 0
        meta_penalty = (diff_weight ** 2) * 4 if diff_weight >= 8 else 0
        entropy = max(entropy_base + ghost_penalty + meta_penalty, 1.0)
        exergy_ratio = opp.reward_usd / entropy
        
        console.print(
            f"  {i}. [bold]{opp.title[:60]}[/bold]\n"
            f"     Platform: [cyan]{opp.platform}[/cyan] | "
            f"Repo: [dim]{opp.repo}[/dim]\n"
            f"     Reward: [green]${opp.reward_usd:,.0f}[/green] | "
            f"EV: [yellow]${opp.ev:,.0f}[/yellow] | "
            f"ExRatio: [magenta]{exergy_ratio:.2f}[/magenta] | "
            f"Gate: {gate}\n"
            f"     URL: [dim]{opp.url}[/dim]\n"
        )
