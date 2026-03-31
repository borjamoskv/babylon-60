"""Vector L CLI — PYME Bottleneck Hunter commands.

Commands:
    cortex vector-l scan    — Scan sources for PYME bottleneck signals
    cortex vector-l pitch   — Manually pitch a specific prospect
    cortex vector-l status  — Agent status and pipeline counts
    cortex vector-l revenue — MRR tracker: converted × tier
    cortex vector-l list    — List prospects by stage
    cortex vector-l convert — Mark a prospect as converted (paying)
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


@click.group("vector-l")
def vector_l_cmds():
    """Vector L — PYME bottleneck detection and CORTEX agent sales engine."""


# ── scan ──────────────────────────────────────────────────────────────────────


@vector_l_cmds.command("scan")
@click.option(
    "--sources",
    default="linkedin,indeed",
    show_default=True,
    help="Comma-separated probe sources: linkedin,glassdoor,github,indeed",
)
@click.option(
    "--query",
    default="data entry OR office manager OR administrative",
    show_default=True,
    help="Search query for job signal probes",
)
@click.option("--limit", default=30, show_default=True, help="Max prospects per probe")
@click.option(
    "--min-gap",
    default=0.55,
    show_default=True,
    type=float,
    help="Minimum exergy gap to include in output",
)
@click.option("--dry-run", is_flag=True, help="Score only — do not send pitches")
def scan(sources: str, query: str, limit: int, min_gap: float, dry_run: bool):
    """Scan public sources for PYMEs with operational bottlenecks."""
    from cortex.agents.builtins.vector_l_ledger import VectorLLedger
    from cortex.agents.builtins.vector_l_probe import (
        GitHubOrgProbe,
        GlassdoorProbe,
        IndeedProbe,
        LinkedInProbe,
        score_company,
        tier_from_score,
    )

    source_map = {
        "linkedin": LinkedInProbe,
        "glassdoor": GlassdoorProbe,
        "github": GitHubOrgProbe,
        "indeed": IndeedProbe,
    }

    active_sources = [s.strip().lower() for s in sources.split(",") if s.strip()]
    probes = [source_map[s]() for s in active_sources if s in source_map]

    if not probes:
        console.print("[red]No valid sources. Use: linkedin,glassdoor,github,indeed[/red]")
        sys.exit(1)

    console.print(
        f"[bold cyan]🔍 Vector L — Scanning ({', '.join(active_sources)}) ...[/bold cyan]"
    )
    if dry_run:
        console.print("[yellow]⚠️  DRY RUN — no pitches will be sent[/yellow]")

    async def _run():
        import asyncio

        tasks = [p.scan(query=query, limit=limit) for p in probes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals = []
        for r in results:
            if isinstance(r, list):
                signals.extend(r)

        # Group by company → score
        from collections import defaultdict

        company_map = defaultdict(list)
        for sig in signals:
            company_map[sig.company].append(sig)

        ledger = VectorLLedger()
        scored_rows = []
        for company, sigs in company_map.items():
            gap = score_company(sigs)
            tier = tier_from_score(gap)
            if gap < min_gap:
                continue
            evidence = "; ".join(s.evidence for s in sigs[:2])
            src_list = list({s.source for s in sigs})
            scored_rows.append((company, gap, tier, evidence, src_list))
            if not dry_run:
                pid = await ledger.discover(
                    company=company, sources=src_list, signals_summary=evidence
                )
                await ledger.score(prospect_id=pid, company=company, exergy_gap=gap, tier=tier)

        return sorted(scored_rows, key=lambda x: x[1], reverse=True)

    rows = asyncio.run(_run())

    if not rows:
        console.print(
            "[dim]No companies above threshold. Try lowering --min-gap or expanding --query.[/dim]"
        )
        return

    table = Table(title=f"Vector L — {len(rows)} prospects found", box=box.SIMPLE_HEAVY)
    table.add_column("Company", style="bold white", min_width=25)
    table.add_column("Exergy Gap", justify="right", style="cyan")
    table.add_column("Tier", justify="right", style="green")
    table.add_column("Sources", style="dim")
    table.add_column("Evidence", style="dim", max_width=50)

    for company, gap, tier, evidence, srcs in rows:
        tier_str = f"[green]${tier}/mo[/green]" if tier > 0 else "[dim]below threshold[/dim]"
        table.add_row(
            company,
            f"{gap:.3f}",
            tier_str,
            ", ".join(srcs),
            evidence[:80],
        )

    console.print(table)


# ── pitch ─────────────────────────────────────────────────────────────────────


@vector_l_cmds.command("pitch")
@click.option("--company", required=True, help="Company name to pitch")
@click.option(
    "--tier",
    type=click.Choice(["500", "1000", "2000"]),
    default="500",
    show_default=True,
    help="Monthly pricing tier in USD",
)
@click.option("--to-email", default="", help="Recipient email address")
@click.option("--evidence", default="", help="Bottleneck evidence for personalization")
@click.option("--source", default="linkedin", help="Signal source context")
@click.option("--dry-run", is_flag=True, help="Compose and print — do not send")
def pitch_cmd(company: str, tier: str, to_email: str, evidence: str, source: str, dry_run: bool):
    """Compose and dispatch a CORTEX agent pitch to a specific company."""
    from cortex.agents.builtins.vector_l_ledger import VectorLLedger
    from cortex.agents.builtins.vector_l_pitcher import EmailDispatcher, PitchComposer

    tier_int = int(tier)

    async def _run():
        composer = PitchComposer()
        email_svc = EmailDispatcher()
        ledger = VectorLLedger()

        console.print(
            f"[bold cyan]✍️  Composing pitch for {company} (${tier_int}/mo)...[/bold cyan]"
        )
        composed = await composer.compose(
            company=company,
            signals_summary=evidence or f"Multiple {source} signals",
            tier=tier_int,
            sources=[source],
        )

        console.print(f"\n[bold]Subject:[/bold] {composed['subject']}")
        console.print(f"[bold]Variant:[/bold] {composed['variant']}")
        console.print(f"\n[dim]{'─' * 60}[/dim]")
        console.print(composed["body"])
        console.print(f"[dim]{'─' * 60}[/dim]\n")

        if dry_run:
            console.print("[yellow]⚠️  DRY RUN — email not sent[/yellow]")
            return

        if not to_email:
            console.print("[red]❌ --to-email required when not using --dry-run[/red]")
            sys.exit(1)

        sent = await email_svc.send(
            to_email=to_email,
            subject=composed["subject"],
            body=composed["body"],
            dry_run=False,
        )

        if sent:
            console.print(f"[green]✅ Pitch sent to {to_email}[/green]")
            pid = f"vl_{company[:20].lower().replace(' ', '_')}_manual"
            await ledger.pitch(
                prospect_id=pid,
                company=company,
                tier=tier_int,
                channel="email",
                pitch_preview=composed["body"][:120],
            )
        else:
            console.print("[red]❌ Send failed. Check VECTOR_L_SMTP_* env vars.[/red]")

    asyncio.run(_run())


# ── status ────────────────────────────────────────────────────────────────────


@vector_l_cmds.command("status")
def status_cmd():
    """Show Vector L agent pipeline status and stats."""
    import os

    from cortex.agents.builtins.vector_l_ledger import ProspectStage, VectorLLedger

    ledger = VectorLLedger()
    all_prospects = ledger.list_prospects()
    stages = {s.value: 0 for s in ProspectStage}
    for p in all_prospects:
        stage = p.get("metadata", {}).get("stage", "UNKNOWN")
        stages[stage] = stages.get(stage, 0) + 1

    table = Table(title="Vector L — Pipeline Status", box=box.SIMPLE_HEAVY)
    table.add_column("Stage", style="bold white")
    table.add_column("Count", justify="right", style="cyan")

    for stage, count in stages.items():
        style = ""
        if stage == "CONVERTED":
            style = "bold green"
        elif stage == "PITCHED":
            style = "yellow"
        elif stage == "FILTERED":
            style = "dim"
        table.add_row(f"[{style}]{stage}[/{style}]" if style else stage, str(count))

    console.print(table)

    mrr = ledger.mrr_total()
    console.print(f"\n💰 [bold green]Total MRR: ${mrr:,}/mo[/bold green]")

    smtp_ok = bool(os.environ.get("VECTOR_L_SMTP_USER") and os.environ.get("VECTOR_L_SMTP_PASS"))
    li_ok = bool(os.environ.get("VECTOR_L_LINKEDIN_SESSION"))
    console.print(
        f"\nChannels: Email={'[green]✓[/green]' if smtp_ok else '[red]✗[/red]'}  "
        f"LinkedIn={'[green]✓[/green]' if li_ok else '[dim]optional[/dim]'}"
    )


# ── revenue ───────────────────────────────────────────────────────────────────


@vector_l_cmds.command("revenue")
def revenue_cmd():
    """Show MRR from converted prospects."""
    from cortex.agents.builtins.vector_l_ledger import ProspectStage, VectorLLedger

    ledger = VectorLLedger()
    converted = ledger.list_prospects(stage=ProspectStage.CONVERTED)

    if not converted:
        console.print(
            "[dim]No conversions yet. Run `cortex vector-l scan` and `pitch` first.[/dim]"
        )
        return

    table = Table(title="Vector L — Revenue", box=box.SIMPLE_HEAVY)
    table.add_column("Company", style="bold white")
    table.add_column("Tier", justify="right", style="green")
    table.add_column("Hours Saved/mo", justify="right", style="cyan")
    table.add_column("Sub ID", style="dim")

    total_mrr = 0
    total_hours = 0.0
    for fact in converted:
        meta = fact.get("metadata", {})
        company = meta.get("company", "?")
        tier = meta.get("tier_usd", 0)
        hours = fact.get("hours_saved", 0.0)
        sub_id = meta.get("subscription_id", "—")
        table.add_row(company, f"${tier}", f"{hours:.0f}h", sub_id)
        total_mrr += tier
        total_hours += hours

    console.print(table)
    console.print(
        f"\n💰 [bold green]MRR: ${total_mrr:,}/mo[/bold green]  |  "
        f"⏱  Hours delivered: {total_hours:.0f}h/mo"
    )


# ── list ──────────────────────────────────────────────────────────────────────


@vector_l_cmds.command("list")
@click.option(
    "--stage",
    default=None,
    type=click.Choice(
        ["DISCOVERED", "SCORED", "PITCHED", "RESPONDED", "CONVERTED", "CHURNED", "FILTERED"]
    ),
    help="Filter by pipeline stage",
)
@click.option("--limit", default=20, show_default=True, help="Max rows to display")
def list_cmd(stage: str | None, limit: int):
    """List prospects in the Vector L pipeline."""
    from cortex.agents.builtins.vector_l_ledger import ProspectStage, VectorLLedger

    ledger = VectorLLedger()
    ps = ProspectStage(stage) if stage else None
    prospects = ledger.list_prospects(stage=ps)[:limit]

    if not prospects:
        console.print(f"[dim]No prospects{f' with stage {stage}' if stage else ''}.[/dim]")
        return

    table = Table(title=f"Vector L Prospects ({len(prospects)})", box=box.SIMPLE_HEAVY)
    table.add_column("Company", style="bold white", min_width=20)
    table.add_column("Stage", style="cyan")
    table.add_column("Tier", justify="right", style="green")
    table.add_column("Exergy Gap", justify="right")
    table.add_column("Evidence", style="dim", max_width=50)

    for fact in prospects:
        meta = fact.get("metadata", {})
        # ts = fact.get("timestamp", 0)
        # dt = datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else "?"
        table.add_row(
            meta.get("company", "?"),
            meta.get("stage", "?"),
            f"${meta.get('tier_usd', 0)}",
            f"{meta.get('exergy_gap', 0):.3f}",
            fact.get("evidence", "")[:80],
        )

    console.print(table)


# ── convert ───────────────────────────────────────────────────────────────────


@vector_l_cmds.command("convert")
@click.option("--prospect-id", required=True, help="Prospect ID from `vector-l list`")
@click.option("--company", required=True, help="Company name")
@click.option(
    "--tier",
    required=True,
    type=click.Choice(["500", "1000", "2000"]),
    help="Monthly subscription tier in USD",
)
@click.option("--subscription-id", default="", help="Stripe/payment subscription ID")
def convert_cmd(prospect_id: str, company: str, tier: str, subscription_id: str):
    """Record a successful conversion (prospect → paying customer)."""
    from cortex.agents.builtins.vector_l_ledger import VectorLLedger

    tier_int = int(tier)

    async def _run():
        ledger = VectorLLedger()
        await ledger.convert(
            prospect_id=prospect_id,
            company=company,
            tier=tier_int,
            subscription_id=subscription_id,
        )
        console.print(
            f"[bold green]✅ CONVERTED: {company} at ${tier_int}/mo[/bold green]  "
            f"| MRR: ${ledger.mrr_total():,}/mo"
        )

    asyncio.run(_run())
