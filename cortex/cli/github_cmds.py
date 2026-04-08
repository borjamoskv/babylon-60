"""CLI commands: github sync, github status."""

from __future__ import annotations

import os
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, _run_async, cli, console, get_engine
from cortex.services.github_agent_demo import build_github_agent_payload, run_github_agent_demo
from cortex.services.github_shortcuts import (
    GitHubShortcutError,
    GitHubShortcutService,
    parse_line_spec,
    run_gh,
)

__all__ = ["github_cmds"]


@cli.group("github")
def github_cmds() -> None:
    """GitHub ↔ CORTEX bridge — sync issues/PRs as facts."""
    pass


def _get_shortcut_service(remote: str) -> GitHubShortcutService:
    try:
        return GitHubShortcutService.from_repo(remote=remote)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err


def _emit_shortcut_url(title: str, url: str, open_browser: bool) -> None:
    opened = False
    if open_browser:
        opened = GitHubShortcutService.open_url(url)

    console.print(f"[bold cyan]{title}[/]")
    console.print(url, style="cyan", soft_wrap=True, highlight=False)
    if opened:
        console.print("[dim]Opened in your browser.[/dim]")
    else:
        console.print("[dim]Copy or open this URL.[/dim]")


def _repo_cwd(remote: str) -> Path:
    return _get_shortcut_service(remote).context.repo_root


def _run_gh_shortcut(args: list[str], *, cwd: Path | None = None) -> None:
    try:
        run_gh(args, cwd=cwd)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err


def _emit_json_result(payload: dict[str, object]) -> None:
    console.print_json(data=payload)


@github_cmds.command()
@click.option("--token", envvar="GITHUB_TOKEN", default=None, help="GitHub PAT (or GITHUB_TOKEN)")
@click.option("--owner", default="borjamoskv", help="GitHub user/org to scan")
@click.option("--repo", default=None, help="Sync only this repo (name, not full path)")
@click.option(
    "--tenant-id",
    default="default",
    show_default=True,
    help="Tenant scope for deduplication and persistence.",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def sync(token: str | None, owner: str, repo: str | None, tenant_id: str, db: str) -> None:
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
            bridge = GitHubCortexBridge(engine, token=token, owner=owner, tenant_id=tenant_id)

            with console.status("[bold blue]Syncing GitHub → CORTEX...[/]"):
                result = await bridge.sync_all(repo_filter=repo)

            await bridge.close()

            console.print(
                Panel(
                    f"[bold green]✓ GitHub Sync Complete[/]\n"
                    f"Tenant: {tenant_id}\n"
                    f"Repos scanned: {result.repos_scanned}\n"
                    f"Issues → bridges: {result.issues_synced}\n"
                    f"PRs → bridges: {result.prs_synced}\n"
                    f"Crystallized → decisions: {result.crystallized}\n"
                    f"Skipped (already synced): {result.skipped}",
                    title="🌉 GitHub → CORTEX",
                    border_style="cyan",
                )
            )

            for err in result.errors:
                console.print(f"  [red]✗ {err}[/]")

        finally:
            await engine.close()

    _run_async(_async_sync())


@github_cmds.command()
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option(
    "--tenant-id",
    default="default",
    show_default=True,
    help="Tenant scope for bridge status counts.",
)
def status(db: str, tenant_id: str) -> None:
    """Show GitHub bridge sync status."""
    engine = get_engine(db)

    async def _async_status():
        try:
            await engine.init_db()
            async with engine.session() as conn:
                # Count active bridges
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM facts "
                    "WHERE fact_type = 'bridge' AND source = 'bridge:github' "
                    "AND valid_until IS NULL AND tenant_id = ?",
                    (tenant_id,),
                )
                row = await cursor.fetchone()
                bridge_count = row[0] if row else 0

                # Count crystallized decisions
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM facts "
                    "WHERE fact_type = 'decision' AND source = 'bridge:github' "
                    "AND valid_until IS NULL AND tenant_id = ?",
                    (tenant_id,),
                )
                row = await cursor.fetchone()
                decision_count = row[0] if row else 0

                # Last sync time
                cursor = await conn.execute(
                    "SELECT MAX(created_at) FROM facts WHERE source = 'bridge:github' "
                    "AND tenant_id = ?",
                    (tenant_id,),
                )
                row = await cursor.fetchone()
                last_sync = row[0] if row and row[0] else "Never"

            table = Table(
                title=f"🌉 GitHub Bridge Status [{tenant_id}]",
                border_style="cyan",
            )
            table.add_column("Metric", style="bold")
            table.add_column("Value", style="cyan")
            table.add_row("Tenant", tenant_id)
            table.add_row("Active bridges (open issues/PRs)", str(bridge_count))
            table.add_row("Crystallized decisions (closed)", str(decision_count))
            table.add_row("Last sync", str(last_sync))

            console.print(table)

        finally:
            await engine.close()

    _run_async(_async_status())


@github_cmds.command("dev")
@click.argument("path", required=False)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def dev(path: str | None, remote: str, open_browser: bool) -> None:
    """Build a `github.dev` URL for the current repo or file."""
    service = _get_shortcut_service(remote)
    try:
        url = service.dev_url(path)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub Dev", url, open_browser)


@github_cmds.command("permalink")
@click.argument("path", required=False)
@click.option("--lines", default=None, help="Single line or range, e.g. `10` or `10-25`.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def permalink(path: str | None, lines: str | None, remote: str, open_browser: bool) -> None:
    """Build a commit-pinned GitHub URL, similar to pressing `y` in the browser."""
    service = _get_shortcut_service(remote)
    try:
        start_line, end_line = parse_line_spec(lines)
        url = service.permalink_url(path, start_line=start_line, end_line=end_line)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub Permalink", url, open_browser)


@github_cmds.command("search")
@click.argument("query", required=False, default="")
@click.option("--path", "path_filter", default=None, help="Optional path: qualifier.")
@click.option("--lang", "language", default=None, help="Optional lang: qualifier.")
@click.option("--symbol", default=None, help="Optional symbol: qualifier.")
@click.option("--all-repos", is_flag=True, help="Search globally instead of scoping to this repo.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def search(
    query: str,
    path_filter: str | None,
    language: str | None,
    symbol: str | None,
    all_repos: bool,
    remote: str,
    open_browser: bool,
) -> None:
    """Build a GitHub code search URL with qualifiers."""
    service = _get_shortcut_service(remote)
    try:
        url = service.search_url(
            query,
            path=path_filter,
            language=language,
            symbol=symbol,
            repo_scoped=not all_repos,
        )
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub Search", url, open_browser)


@github_cmds.command("diff-url")
@click.option("--pr", "pr_number", type=int, default=None, help="Pull request number.")
@click.option("--commit", "commit_sha", default=None, help="Commit SHA.")
@click.option(
    "--format",
    "format_name",
    type=click.Choice(["patch", "diff"], case_sensitive=False),
    default="patch",
    show_default=True,
    help="Requested export format.",
)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def diff_url(
    pr_number: int | None,
    commit_sha: str | None,
    format_name: str,
    remote: str,
    open_browser: bool,
) -> None:
    """Build a `.patch` or `.diff` URL for a PR or commit."""
    service = _get_shortcut_service(remote)
    try:
        url = service.diff_url(pr_number=pr_number, commit_sha=commit_sha, format_name=format_name)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub Diff Export", url, open_browser)


@github_cmds.command("review")
@click.argument("pr_number", type=int)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def review(pr_number: int, remote: str, open_browser: bool) -> None:
    """Open the PR commits view, useful when the full diff is too noisy."""
    service = _get_shortcut_service(remote)
    url = service.review_url(pr_number)
    _emit_shortcut_url("GitHub PR Commits", url, open_browser)


@github_cmds.command("blame")
@click.argument("path")
@click.option("--ref", "git_ref", default=None, help="Branch, tag, or SHA to inspect.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def blame(path: str, git_ref: str | None, remote: str, open_browser: bool) -> None:
    """Build a blame URL for a tracked file."""
    service = _get_shortcut_service(remote)
    try:
        url = service.blame_url(path, ref=git_ref)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub Blame", url, open_browser)


@github_cmds.command("history")
@click.argument("path")
@click.option("--ref", "git_ref", default=None, help="Branch, tag, or SHA to inspect.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to resolve the GitHub repository.",
)
@click.option("--open", "open_browser", is_flag=True, help="Open the URL in your browser.")
def history(path: str, git_ref: str | None, remote: str, open_browser: bool) -> None:
    """Build a file history URL for a tracked file."""
    service = _get_shortcut_service(remote)
    try:
        url = service.history_url(path, ref=git_ref)
    except GitHubShortcutError as err:
        raise click.ClickException(str(err)) from err
    _emit_shortcut_url("GitHub File History", url, open_browser)


@github_cmds.command("agent-demo")
@click.option("--op", default="status", show_default=True, help="GitHubAgent operation.")
@click.option("--remote", default="origin", show_default=True, help="Git remote to resolve.")
@click.option("--path", default=None, help="Repo-relative path for file-oriented ops.")
@click.option("--lines", default=None, help="Line selection, e.g. `10` or `10-25`.")
@click.option("--query", default=None, help="Search query for the search op.")
@click.option("--language", default=None, help="Language qualifier for search.")
@click.option("--symbol", default=None, help="Symbol qualifier for search.")
@click.option("--all-repos", is_flag=True, help="Disable repo: scoping in search.")
@click.option("--pr-number", type=int, default=None, help="Pull request number.")
@click.option("--commit-sha", default=None, help="Commit SHA for diff_url.")
@click.option("--format-name", default=None, help="Format for diff_url, usually patch or diff.")
@click.option("--ref", "git_ref", default=None, help="Git ref for blame/history.")
@click.option("--title", default=None, help="PR title for pr_create.")
@click.option("--body", default=None, help="PR body for pr_create.")
@click.option("--base", default=None, help="Base branch for pr_create.")
@click.option("--head", default=None, help="Head branch for pr_create.")
@click.option("--draft", is_flag=True, help="Create a draft PR.")
@click.option("--fill", is_flag=True, help="Ask gh to fill title/body from commits.")
@click.option("--web", is_flag=True, help="Open browser flow for supported gh ops.")
@click.option("--name-with-owner", default=None, help="owner/repo identifier for repo_clone.")
@click.option("--directory", default=None, help="Destination directory for repo_clone.")
@click.option("--timeout", default=5.0, type=float, show_default=True, help="Wait time in seconds.")
def agent_demo(
    op: str,
    remote: str,
    path: str | None,
    lines: str | None,
    query: str | None,
    language: str | None,
    symbol: str | None,
    all_repos: bool,
    pr_number: int | None,
    commit_sha: str | None,
    format_name: str | None,
    git_ref: str | None,
    title: str | None,
    body: str | None,
    base: str | None,
    head: str | None,
    draft: bool,
    fill: bool,
    web: bool,
    name_with_owner: str | None,
    directory: str | None,
    timeout: float,
) -> None:
    """Run the GitHubAgent once against the current repository and print JSON."""
    payload = build_github_agent_payload(
        op=op,
        remote=remote,
        path=path,
        lines=lines,
        query=query,
        language=language,
        symbol=symbol,
        all_repos=all_repos,
        pr_number=pr_number,
        commit_sha=commit_sha,
        format_name=format_name,
        ref=git_ref,
        title=title,
        body=body,
        base=base,
        head=head,
        draft=draft,
        fill=fill,
        web=web,
        name_with_owner=name_with_owner,
        directory=directory,
    )
    result = _run_async(run_github_agent_demo(payload, timeout=timeout))
    _emit_json_result(result)
    if "error" in result:
        raise SystemExit(1)


@github_cmds.group("pr")
def github_pr_cmds() -> None:
    """Thin wrappers around high-value `gh pr` commands."""
    pass


@github_pr_cmds.command("checkout")
@click.argument("pr_number", type=int)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to locate the repo before running `gh`.",
)
def pr_checkout(pr_number: int, remote: str) -> None:
    """Run `gh pr checkout` in the current repository."""
    _run_gh_shortcut(["pr", "checkout", str(pr_number)], cwd=_repo_cwd(remote))


@github_pr_cmds.command("view")
@click.argument("pr_number", type=int)
@click.option("--web", is_flag=True, help="Open the PR in the browser.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to locate the repo before running `gh`.",
)
def pr_view(pr_number: int, web: bool, remote: str) -> None:
    """Run `gh pr view`, optionally with `--web`."""
    args = ["pr", "view", str(pr_number)]
    if web:
        args.append("--web")
    _run_gh_shortcut(args, cwd=_repo_cwd(remote))


@github_pr_cmds.command("create")
@click.option("--title", default=None, help="PR title.")
@click.option("--body", default=None, help="PR body.")
@click.option("--base", default=None, help="Base branch.")
@click.option("--head", default=None, help="Head branch.")
@click.option("--draft", is_flag=True, help="Create the PR as draft.")
@click.option("--fill", is_flag=True, help="Populate title/body from commits.")
@click.option("--web", is_flag=True, help="Open the browser flow instead of terminal prompts.")
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Git remote used to locate the repo before running `gh`.",
)
def pr_create(
    title: str | None,
    body: str | None,
    base: str | None,
    head: str | None,
    draft: bool,
    fill: bool,
    web: bool,
    remote: str,
) -> None:
    """Run `gh pr create` with a thin, scriptable wrapper."""
    args = ["pr", "create"]
    if title:
        args.extend(["--title", title])
    if body:
        args.extend(["--body", body])
    if base:
        args.extend(["--base", base])
    if head:
        args.extend(["--head", head])
    if draft:
        args.append("--draft")
    if fill:
        args.append("--fill")
    if web:
        args.append("--web")
    _run_gh_shortcut(args, cwd=_repo_cwd(remote))


@github_cmds.group("repo")
def github_repo_cmds() -> None:
    """Thin wrappers around high-value `gh repo` commands."""
    pass


@github_repo_cmds.command("clone")
@click.argument("name_with_owner")
@click.argument("directory", required=False)
def repo_clone(name_with_owner: str, directory: str | None) -> None:
    """Run `gh repo clone owner/repo [directory]`."""
    args = ["repo", "clone", name_with_owner]
    if directory:
        args.append(directory)
    _run_gh_shortcut(args)
