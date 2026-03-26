# CORTEX-TAINT: antigravity:c0d3abfe:2026-03-26T14:36:00Z
"""CLI commands: github sync, github status."""

from __future__ import annotations

import asyncio
import base64
import os

import click
import httpx
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


@github_cmds.command()
@click.argument("repo_path", required=True)
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub PAT")
@click.option(
    "--owner", default="borjamoskv", help="GitHub username where the Profile README is located."
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def repost(repo_path: str, token: str | None, owner: str, db: str) -> None:
    """Repost a GitHub repository to your Profile README (simulating SoundCloud Repost)."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗[/] GitHub token required.")
        raise SystemExit(1)

    engine = get_engine(db)

    async def _async_repost():
        from cortex.memory.temporal import now_iso

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient() as client:
            with console.status(f"[bold blue]Fetching metadata for {repo_path}...[/]"):
                repo_res = await client.get(
                    f"https://api.github.com/repos/{repo_path}", headers=headers
                )
                if repo_res.status_code != 200:
                    console.print(f"[red]✗[/] Failed to fetch {repo_path}: {repo_res.text}")
                    return
                repo_data = repo_res.json()

            repo_url = repo_data.get("html_url")
            desc = repo_data.get("description") or "No description provided."
            stars = repo_data.get("stargazers_count", 0)
            lang = repo_data.get("language") or "N/A"
            owner_login = repo_data["owner"]["login"]
            repo_name = repo_data["name"]

            with console.status(f"[bold blue]Fetching Profile README for {owner}/{owner}...[/]"):
                readme_url = f"https://api.github.com/repos/{owner}/{owner}/readme"
                readme_res = await client.get(readme_url, headers=headers)
                if readme_res.status_code != 200:
                    console.print(
                        f"[red]✗[/] Failed to fetch {owner}'s profile README. Do you have a {owner}/{owner} repository?"
                    )
                    return

                readme_data = readme_res.json()
                content_base64 = readme_data["content"]
                sha = readme_data["sha"]

                content = base64.b64decode(content_base64).decode("utf-8")

            # Format the new entry
            repost_entry = (
                f"- 🔄 **[{owner_login}/{repo_name}]({repo_url})** - {desc} (*⭐ {stars} | {lang}*)"
            )

            # Inject into README
            start_marker = "<!-- START_REPOSTS -->"
            end_marker = "<!-- END_REPOSTS -->"

            if start_marker in content and end_marker in content:
                # Insert right after START_REPOSTS
                pre_marker, post_marker = content.split(start_marker, 1)
                inside, after_marker = post_marker.split(end_marker, 1)

                # Check if it's already reposted
                if repo_url in inside:
                    console.print(
                        f"[yellow]![/] Repository {repo_path} is already reposted in your profile."
                    )
                    return

                new_content = (
                    pre_marker
                    + start_marker
                    + "\n"
                    + repost_entry
                    + inside
                    + end_marker
                    + after_marker
                )
            else:
                # Append to bottom if markers not found
                if repo_url in content:
                    console.print(
                        f"[yellow]![/] Repository {repo_path} is already in your profile README."
                    )
                    return

                console.print(
                    f"[yellow]![/] {start_marker} and {end_marker} not found in README. Appending to the bottom."
                )
                new_content = (
                    content + f"\n\n### 🔄 Reposts\n{start_marker}\n{repost_entry}\n{end_marker}\n"
                )

            with console.status(
                f"[bold blue]Committing injected 'repost' to {owner}/{owner}...[/]"
            ):
                update_payload = {
                    "message": f"cortex: repost {repo_path} \N{SATELLITE ANTENNA}",
                    "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
                    "sha": sha,
                }

                update_res = await client.put(readme_url, headers=headers, json=update_payload)
                if update_res.status_code != 200:
                    console.print(f"[red]✗[/] Failed to update README: {update_res.text}")
                    return

            try:
                await engine.init_db()
                await engine.store(
                    project="github-reposts",
                    content=f"[Repost] {repo_path}: {desc}",
                    fact_type="action",
                    tags=["github", "repost", "profile"],
                    confidence="C5",
                    source="bridge:github:repost",
                    meta={"repo": repo_path, "url": repo_url, "timestamp": now_iso()},
                )
            finally:
                await engine.close()

            # Output success
            console.print(
                Panel(
                    f"[bold white]SYSTEM: REPOST_INJECTED[/]\n"
                    f"[dim]─── Target ───[/]\n"
                    f"Repository: [cyan]{repo_path}[/]\n"
                    f"Stars: [yellow]⭐ {stars}[/]\n"
                    f"Language: [blue]{lang}[/]\n"
                    f"[dim]─── Destination ───[/]\n"
                    f"Profile: [green]github.com/{owner}[/]\n"
                    f"[dim]──────────────────[/]",
                    title="[bold blue]🌉 CORTEX :: REPOST[/]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

    _run_async(_async_repost())


@github_cmds.command()
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub PAT")
@click.option("--repo", required=True, help="Repository to track (e.g., owner/repo)")
@click.option("--pr", required=True, type=int, help="Pull Request number to analyze")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def shield(token: str | None, repo: str, pr: int, db: str) -> None:
    """Analyze a PR diff for exfiltration and structural threats."""
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗[/] GitHub token required.")
        raise SystemExit(1)

    engine = get_engine(db)

    async def _async_shield():
        import re

        from cortex.memory.temporal import now_iso

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
        }

        async with httpx.AsyncClient() as client:
            with console.status(
                f"[bold red]CORTEX IMMUNE SYSTEM // Extracting PR #{pr} diff from {repo}...[/]"
            ):
                res = await client.get(
                    f"https://api.github.com/repos/{repo}/pulls/{pr}", headers=headers
                )

                if res.status_code != 200:
                    console.print(f"[red]✗[/] Failed to fetch PR diff: HTTP {res.status_code}")
                    return

                diff_text = res.text

            with console.status(
                "[bold yellow]Analyzing diff for thermodynamic exfiltration and anomalies...[/]"
            ):
                threats_found = []

                if ".github/workflows" in diff_text:
                    threats_found.append(
                        "[CRITICAL] Modification of CI/CD pipeline detected (.github/workflows)."
                    )
                if re.search(
                    r"(process\.env|os\.environ|GITHUB_TOKEN|npm\s+config\s+set)",
                    diff_text,
                    re.IGNORECASE,
                ):
                    threats_found.append(
                        "[HIGH] Environment variable exfiltration or credential access pattern detected."
                    )
                if (
                    re.search(r"(curl|wget|fetch|axios).*?(http)", diff_text, re.IGNORECASE)
                    and "+" in diff_text
                ):
                    threats_found.append("[MEDIUM] New external network request detected in diff.")
                if (
                    re.search(r"(base64|Buffer\.from\(|btoa\()", diff_text, re.IGNORECASE)
                    and "+" in diff_text
                ):
                    threats_found.append(
                        "[HIGH] Hex/Base64 encoding routines added (potential obfuscation)."
                    )

                await asyncio.sleep(1.2)

            console.print(
                Panel(
                    f"[bold white]SYSTEM: PR_SHIELD_ANALYSIS[/]\n"
                    f"[dim]─── Target ───[/]\n"
                    f"Repository: [cyan]{repo}[/]\n"
                    f"PR Number:  [yellow]#{pr}[/]\n"
                    f"Diff Lines: [blue]{len(diff_text.splitlines())}[/]\n"
                    f"[dim]─── Diagnostics ───[/]\n",
                    title="[bold red]🛡️ CORTEX :: GITHUB_SHIELD[/]",
                    border_style="red" if threats_found else "green",
                )
            )

            if threats_found:
                console.print("[bold red]🚨 ENTROPÍA MALICIOSA DETECTADA 🚨[/]")
                for threat in threats_found:
                    console.print(f"  - {threat}")
                console.print(
                    "\n[bold yellow]Recomendación operativa:[/] Abortar merge. CORTEX ha bloqueado simbólicamente esta PR en el ledger."
                )
            else:
                console.print(
                    "[bold green]✅ DIFF LIMPIO[/]. No se detectan fugas exérgicas ni extracciones de tokens ambientales."
                )
                console.print(
                    "\n[bold cyan]Recomendación operativa:[/] Merge seguro bajo tu propia discreción humana."
                )

            try:
                await engine.init_db()
                await engine.store(
                    project="pr-shield",
                    content=f"[PR Shield] Analyzed {repo}#{pr}. Threats: {len(threats_found)}",
                    fact_type="security_audit",
                    tags=["github", "security", "pr-shield", repo.split("/")[-1]],
                    confidence="C5",
                    source="bridge:github:shield",
                    meta={"repo": repo, "pr": pr, "threats": threats_found, "timestamp": now_iso()},
                )
            finally:
                await engine.close()

    _run_async(_async_shield())
