import asyncio
import logging

import click
from rich.table import Table

from cortex.cli.common import cli, console
from cortex.extensions.x_intelligence.engine import XIntelligenceEngine

LOG = logging.getLogger("cortex.cli.x_cmds")


@cli.group("x")
def x_cmds():
    """Forensic-Grade X Intelligence."""
    pass


@x_cmds.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Number of tweets to scrape.")
@click.option("--persist/--no-persist", default=True, help="Persist results to CORTEX Ledger.")
@click.option("--project", "-p", default="x-intelligence", help="Target project for persistence.")
@click.option("--proxy", help="Optional proxy URL (e.g. mobile proxy).")
def search_cmd(query: str, limit: int, persist: bool, project: str, proxy: str | None):
    """Search X for real-time intelligence."""
    engine = XIntelligenceEngine(proxy=proxy)

    async def run():
        try:
            if persist:
                response = await engine.search_and_persist(query, limit=limit, project=project)
            else:
                response = await engine.client.search(query, limit=limit)

            table = Table(title=f"X Search: {query}", show_header=True, header_style="bold blue")
            table.add_column("Author", style="cyan")
            table.add_column("Tweet", style="white")
            table.add_column("Likes", justify="right", style="green")

            for tweet in response.tweets:
                author = f"@{tweet.user.screen_name}" if tweet.user else "unknown"
                table.add_row(author, tweet.full_text[:100] + "...", str(tweet.favorite_count))

            console.print(table)
            if persist:
                console.print(
                    f"\n[CORTEX] ✅ Saved {len(response.tweets)} tweets to project: {project}"
                )
        finally:
            await engine.close()

    asyncio.run(run())


@x_cmds.command("user")
@click.argument("screen_name")
@click.option("--persist/--no-persist", default=True, help="Persist results to CORTEX Ledger.")
@click.option("--project", "-p", default="x-intelligence", help="Target project for persistence.")
def user_cmd(screen_name: str, persist: bool, project: str):
    """Fetch X user profile intelligence."""
    engine = XIntelligenceEngine()

    async def run():
        try:
            if persist:
                user = await engine.get_user_and_persist(screen_name, project=project)
            else:
                user = await engine.client.get_user_by_screen_name(screen_name)

            if not user:
                console.print(f"[X] ❌ User @{screen_name} not found.")
                return

            console.print(f"\n[bold blue]X User: @{user.screen_name}[/bold blue]")
            console.print(f"Name: {user.name}")
            console.print(f"Followers: {user.followers_count:,}")
            console.print(f"Bio: {user.description}")

            if persist:
                console.print(f"\n[CORTEX] ✅ User profile persisted to project: {project}")
        finally:
            await engine.close()

    asyncio.run(run())
