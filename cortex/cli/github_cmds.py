"""CLI commands: github sync, github status."""

from __future__ import annotations

import asyncio
import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, console, get_engine

__all__ = ["github_cmds"]


def _run_async(coro):
    return asyncio.run(coro)


@click.group("github")
def github_cmds() -> None:
    """GitHub ↔ CORTEX bridge — sync issues/PRs as facts."""
    pass


@github_cmds.command()
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub PAT (or GITHUB_TOKEN)")
@click.option("--owner", default="borjamoskv", help="GitHub user/org to scan")
@click.option("--repo", default=None, help="Sync only this repo (name, not full path)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(token: str | None, owner: str, repo: str | None, db: str) -> None:
    """Sync GitHub Issues/PRs → CORTEX bridge facts."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗[/] GitHub token required. Set GITHUB_TOKEN env var or pass --token.")
        raise SystemExit(1)

    engine = get_engine(db)

    async def _async_sync():
        from cortex.extensions.sync.github_bridge import GitHubCortexBridge

        try:
            await engine.init_db()
            bridge = GitHubCortexBridge(engine, token=token, owner=owner)

            with console.status(
                "[bold blue]Synchronizing GitHub Architecture → CORTEX Ledger...[/]"
            ):
                result = await bridge.sync_all(repo_filter=repo)

            await bridge.close()

            # Industrial Noir Panel
            console.print(
                Panel(
                    f"[bold white]SYSTEM: GITHUB_SYNC_COMPLETE[/]\n"
                    f"[dim]─── Execution Audit ───[/]\n"
                    f"Repos Scanned: [cyan]{result.repos_scanned}[/]\n"
                    f"Bridges Created: [blue]{result.issues_synced + result.prs_synced}[/]\n"
                    f"Decisions Crystallized: [green]{result.crystallized}[/]\n"
                    f"States Preserved: [yellow]{result.skipped}[/]\n"
                    f"[dim]───────────────────────[/]",
                    title="[bold blue]🌉 CORTEX :: GITHUB[/]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

            for err in result.errors:
                console.print(f"  [bold red]FATAL:[/] {err}")

        finally:
            await engine.close()

    _run_async(_async_sync())


@github_cmds.command()
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub PAT")
@click.option("--repo", required=True, help="Repository to track (e.g., owner/repo)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def stats(token: str | None, repo: str, db: str) -> None:
    """Capture repository metrics as facts."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗[/] GitHub token required.")
        raise SystemExit(1)

    engine = get_engine(db)

    async def _async_stats():
        from cortex.extensions.sync.github_bridge import GitHubCortexBridge
        from cortex.memory.temporal import now_iso

        try:
            await engine.init_db()
            bridge = GitHubCortexBridge(engine, token=token)

            with console.status(f"[bold blue]Extracting metrics from {repo}...[/]"):
                data = await bridge.get_repo_stats(repo)

                # Store as metric fact
                content = f"[GitHub Metrics] {repo}: Stars: {data['stars']}, Forks: {data['forks']}"
                await engine.store(
                    project="github-stats",
                    content=content,
                    fact_type="metric",
                    tags=["github", "metrics", repo.split("/")[-1]],
                    confidence="C5",
                    source="bridge:github:stats",
                    meta={"repo": repo, "metrics": data, "synced_at": now_iso()},
                )

            await bridge.close()

            console.print(f"[bold green]✓ Metrics captured for {repo}:[/]")
            console.print(f"  Stars: [bold cyan]{data['stars']}[/]")
            console.print(f"  Forks: [bold cyan]{data['forks']}[/]")
            console.print(f"  Open Issues: [bold cyan]{data['open_issues']}[/]")

        finally:
            await engine.close()

    _run_async(_async_stats())


@github_cmds.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
def status(db: str) -> None:
    """Show GitHub bridge sync status."""
    engine = get_engine(db)

    async def _async_status():
        try:
            await engine.init_db()
            conn = await engine.get_conn()

            # Count active bridges
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE fact_type = 'bridge' AND source = 'bridge:github' "
                "AND valid_until IS NULL"
            )
            row = await cursor.fetchone()
            bridge_count = row[0] if row else 0

            # Count crystallized decisions
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE fact_type = 'decision' AND source = 'bridge:github' "
                "AND valid_until IS NULL"
            )
            row = await cursor.fetchone()
            decision_count = row[0] if row else 0

            # Last sync time
            cursor = await conn.execute(
                "SELECT MAX(created_at) FROM facts WHERE source = 'bridge:github'"
            )
            row = await cursor.fetchone()
            last_sync = row[0] if row and row[0] else "Never"

            table = Table(
                title="🌉 GitHub Bridge Status",
                border_style="cyan",
            )
            table.add_column("Metric", style="bold")
            table.add_column("Value", style="cyan")
            table.add_row("Active bridges (open issues/PRs)", str(bridge_count))
            table.add_row("Crystallized decisions (closed)", str(decision_count))
            table.add_row("Last sync", str(last_sync))

            console.print(table)

        finally:
            await engine.close()

    _run_async(_async_status())
