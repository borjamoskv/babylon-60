"""CLI Commands — cortex linkedin.

Usage:
    cortex linkedin auth                           # OAuth flow (opens browser)
    cortex linkedin publish --from <md> --url <u>  # Dry-run preview
    cortex linkedin publish --from <md> --url <u> --publish  # Real publish
    cortex linkedin history                        # Audit log
"""

from __future__ import annotations

import webbrowser
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TypedDict, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import cli
from cortex.config import DEFAULT_DB_PATH

console = Console()


class OrganizationPermissionCheck(TypedDict):
    ok: bool | None
    reasons: list[str]
    error: str | None


@click.group(name="linkedin")
def linkedin_cmds() -> None:
    """LinkedIn Posts API — markdown → preview → approve → publish."""
    pass


# ─── AUTH ─────────────────────────────────────────────────────────────────────


@linkedin_cmds.command()
@click.option(
    "--org",
    is_flag=True,
    default=False,
    help="Request w_organization_social scope instead of personal.",
)
@click.option(
    "--organization-urn",
    default="",
    help="Company page URN, e.g. urn:li:organization:12345.",
)
@click.option(
    "--organization-id",
    default="",
    help="Numeric LinkedIn organization ID.",
)
@click.option(
    "--organization-vanity",
    default="",
    help="LinkedIn company vanity name to resolve to an organization URN.",
)
def auth(
    org: bool,
    organization_urn: str,
    organization_id: str,
    organization_vanity: str,
) -> None:
    """Run OAuth 2.0 authorization flow. Prints token for .env storage."""
    from cortex.darknet.linkedin_publisher import (
        LINKEDIN_ORG_SCOPE,
        LINKEDIN_POSTS_SCOPE,
        LinkedInConfig,
        build_auth_url,
        check_organization_post_permission,
        exchange_code_for_token,
        fetch_member_urn,
        resolve_organization_urn,
    )

    try:
        config = LinkedInConfig.from_env()
    except OSError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise click.Abort() from None

    scope = LINKEDIN_ORG_SCOPE if org else LINKEDIN_POSTS_SCOPE
    url, state = build_auth_url(config, scope=scope)

    console.print(
        Panel(
            f"[bold cyan]LinkedIn OAuth — {'Organization' if org else 'Personal'} Scope[/bold cyan]\n\n"
            f"Opening browser to authorize CORTEX...\n"
            f"[dim]State: {state}[/dim]",
            border_style="blue",
        )
    )

    webbrowser.open(url)
    console.print(f"\n[yellow]If browser didn't open, visit:[/yellow]\n{url}\n")

    code = click.prompt("Paste the `code` parameter from the redirect URL")
    returned_state = click.prompt("Paste the `state` parameter to verify CSRF")

    if returned_state != state:
        console.print("[bold red]❌ State mismatch — possible CSRF attack. Aborting.[/bold red]")
        raise click.Abort()

    try:
        token, expiry = exchange_code_for_token(config, code)
        member_urn = fetch_member_urn(token, config.api_version)
    except Exception as e:
        console.print(f"[red]❌ Token exchange failed: {e}[/red]")
        raise click.Abort() from None

    resolved_org_urn = ""
    permission_check: OrganizationPermissionCheck | None = None
    if org:
        requested_org_urn = organization_urn or config.organization_urn
        try:
            resolved_org_urn = resolve_organization_urn(
                token,
                config.api_version,
                organization_urn=requested_org_urn,
                organization_id=organization_id,
                organization_vanity=organization_vanity,
            )
        except Exception as e:
            if organization_urn or organization_id or organization_vanity:
                console.print(f"[red]❌ Organization resolution failed: {e}[/red]")
                raise click.Abort() from None

        if resolved_org_urn:
            permission_check = cast(
                OrganizationPermissionCheck,
                check_organization_post_permission(
                    token,
                    config.api_version,
                    member_urn,
                    resolved_org_urn,
                ),
            )

    console.print("\n[bold green]✅ Authorization successful![/bold green]\n")
    console.print("[yellow]Add these to your .env:[/yellow]")
    console.print(f"[bold]LINKEDIN_ACCESS_TOKEN[/bold]={token}")
    console.print(f"[bold]LINKEDIN_TOKEN_EXPIRY[/bold]={int(expiry)}")
    console.print(f"[bold]LINKEDIN_API_VERSION[/bold]={config.api_version}")
    console.print(f"[bold]LINKEDIN_MEMBER_URN[/bold]={member_urn}")

    if org:
        if resolved_org_urn:
            console.print(f"[bold]LINKEDIN_ORGANIZATION_URN[/bold]={resolved_org_urn}")
            console.print(f"[bold]LINKEDIN_ACTOR_URN[/bold]={resolved_org_urn}")
        else:
            console.print(
                "[bold]LINKEDIN_ORGANIZATION_URN[/bold]=urn:li:organization:<your-company-id>"
            )
            console.print("[bold]LINKEDIN_ACTOR_URN[/bold]=urn:li:organization:<your-company-id>")
            console.print(
                "\n[yellow]No organization selected yet.[/yellow] "
                "Set the company URN before publishing as an organization."
            )
    else:
        console.print(f"[bold]LINKEDIN_ACTOR_URN[/bold]={member_urn}")

    if permission_check:
        if permission_check["ok"] is True:
            console.print(
                "\n[green]Organization permission check:[/green] "
                "[bold]ORGANIC_SHARE_CREATE approved[/bold]"
            )
        elif permission_check["ok"] is False:
            reasons = ", ".join(cast(list[str], permission_check["reasons"])) or "unknown reason"
            console.print(f"\n[red]Organization permission check denied:[/red] {reasons}")
        else:
            console.print(
                "\n[yellow]Organization permission check skipped:[/yellow] "
                f"{permission_check['error']}"
            )


# ─── PUBLISH ──────────────────────────────────────────────────────────────────


@linkedin_cmds.command()
@click.option(
    "--from",
    "md_file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the markdown file.",
)
@click.option(
    "--url",
    "article_url",
    required=True,
    help="Deployed article URL (the link LinkedIn will share).",
)
@click.option(
    "--org",
    is_flag=True,
    default=False,
    help="Publish as a company page using LINKEDIN_ORGANIZATION_URN or the options below.",
)
@click.option("--organization-urn", default="", help="Company page URN.")
@click.option("--organization-id", default="", help="Numeric LinkedIn organization ID.")
@click.option(
    "--organization-vanity",
    default="",
    help="LinkedIn company vanity name to resolve to an organization URN.",
)
@click.option(
    "--publish",
    "do_publish",
    is_flag=True,
    default=False,
    help="Actually publish. Without this flag, dry-run only.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Ignore dedup check and re-publish even if already published.",
)
@click.option(
    "--ai",
    "use_ai",
    is_flag=True,
    default=False,
    help="Generate commentary via LLM instead of raw markdown.",
)
@click.option(
    "--provider",
    "llm_provider",
    default="auto",
    type=click.Choice(["auto", "gemini", "openai", "groq", "deepseek", "openrouter"]),
    help="LLM provider for --ai commentary (default: auto-cascade).",
)
def publish(
    md_file: Path,
    article_url: str,
    org: bool,
    organization_urn: str,
    organization_id: str,
    organization_vanity: str,
    do_publish: bool,
    force: bool,
    use_ai: bool,
    llm_provider: str,
) -> None:
    """
    Publish a markdown article to LinkedIn.

    Default: DRY-RUN (preview only, no network call to LinkedIn).
    Add --publish flag for real publish after human review.
    Add --ai to have an LLM generate the commentary (uses CORTEX LLM Router).
    """
    from cortex.darknet.linkedin_ledger import LinkedInLedger
    from cortex.darknet.linkedin_publisher import (
        LinkedInConfig,
        LinkedInPublisher,
        check_organization_post_permission,
        parse_markdown_article,
        resolve_organization_urn,
    )

    # 1. Parse markdown
    try:
        post = parse_markdown_article(md_file, article_url)
    except Exception as e:
        console.print(f"[red]❌ Failed to parse {md_file}: {e}[/red]")
        raise click.Abort() from None

    # 1b. Optional AI commentary
    if use_ai:
        from cortex.darknet.linkedin_ai import generate_linkedin_commentary_sync

        console.print(f"[cyan]🤖 Generating AI commentary ({llm_provider})...[/cyan]")
        try:
            ai_commentary, p_used = generate_linkedin_commentary_sync(
                title=post.title,
                body=post.commentary,  # raw markdown body
                provider=llm_provider,
            )
            post = replace(post, commentary=ai_commentary)
            console.print(f"[dim]  → {p_used} ✓ ({len(ai_commentary)} chars)[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️  AI commentary failed ({e}), using raw markdown.[/yellow]")

    # 2. Resolve actor scope when available
    dry_run = not do_publish
    config = None
    actor_urn = ""
    prefer_organization = bool(org or organization_urn or organization_id or organization_vanity)

    try:
        config = LinkedInConfig.from_env()
    except OSError as e:
        if do_publish or prefer_organization:
            console.print(f"[red]❌ {e}[/red]")
            raise click.Abort() from None

    if config:
        try:
            resolved_org_urn = resolve_organization_urn(
                config.access_token,
                config.api_version,
                organization_urn=organization_urn or config.organization_urn,
                organization_id=organization_id,
                organization_vanity=organization_vanity,
            )
        except Exception as e:
            console.print(f"[red]❌ Organization resolution failed: {e}[/red]")
            raise click.Abort() from None

        if resolved_org_urn:
            config.organization_urn = resolved_org_urn

        actor_urn = config.resolved_actor_urn(prefer_organization=prefer_organization)

    # 3. Dedup check
    ledger = LinkedInLedger(DEFAULT_DB_PATH)
    content_hash = post.content_hash(actor_urn)

    if not force and not dry_run and ledger.already_published(content_hash):
        console.print(
            f"[yellow]⚠️  Already published (hash: {content_hash}).\n"
            "Use --force to override.[/yellow]"
        )
        raise click.Abort()

    # 4. Preview
    _show_preview(post, content_hash, dry_run, actor_urn)

    if dry_run:
        console.print(
            "\n[bold yellow]🔍 DRY-RUN complete. Review above.[/bold yellow]\n"
            "[dim]Add --publish to post for real.[/dim]"
        )
        # Record dry-run in ledger
        ledger.record(
            content_hash=content_hash,
            source_file=str(md_file),
            article_url=article_url,
            title=post.title,
            git_sha=post.git_sha,
            post_id=f"DRY-{content_hash}",
            post_url="",
            dry_run=True,
            success=True,
        )
        return

    # 5. Human approval gate
    console.print(
        "\n[bold red]⚠️  PUBLISHING to LinkedIn (real post). This cannot be undone.[/bold red]"
    )
    confirmed = click.confirm("Confirm publish?", default=False)
    if not confirmed:
        console.print("[yellow]Aborted.[/yellow]")
        raise click.Abort()

    if config is None:
        console.print("[red]❌ LinkedIn config not available.[/red]")
        raise click.Abort()

    if prefer_organization and not config.organization_urn:
        console.print(
            "[red]❌ Organization publishing requested but no organization URN is configured.[/red]"
        )
        raise click.Abort()

    if prefer_organization and config.member_urn and config.organization_urn:
        permission_check = check_organization_post_permission(
            config.access_token,
            config.api_version,
            config.member_urn,
            config.organization_urn,
        )
        permission_check = cast(OrganizationPermissionCheck, permission_check)
        if permission_check["ok"] is False:
            reasons = ", ".join(cast(list[str], permission_check["reasons"])) or "unknown reason"
            console.print(
                f"[red]❌ Organization permission denied for ORGANIC_SHARE_CREATE:[/red] {reasons}"
            )
            raise click.Abort()
        if permission_check["ok"] is None:
            console.print(
                "[yellow]⚠️  Could not verify organization permission preflight:[/yellow] "
                f"{permission_check['error']}"
            )

    publisher = LinkedInPublisher(config, dry_run=False)

    console.print("\n[cyan]📤 Posting to LinkedIn...[/cyan]")
    try:
        result = publisher.publish(post)
    except Exception as e:
        console.print(f"[red]❌ Publish failed: {e}[/red]")
        ledger.record(
            content_hash=content_hash,
            source_file=str(md_file),
            article_url=article_url,
            title=post.title,
            git_sha=post.git_sha,
            post_id="",
            post_url="",
            dry_run=False,
            success=False,
            error=str(e),
        )
        raise click.Abort() from None

    # 6. Record result
    ledger.record(
        content_hash=content_hash,
        source_file=str(md_file),
        article_url=article_url,
        title=post.title,
        git_sha=post.git_sha,
        post_id=result.get("post_id", ""),
        post_url=result.get("url", "") or "",
        dry_run=False,
        success=result["success"],
        error=result.get("error", "") or "",
    )

    if result["success"]:
        console.print("\n[bold green]✅ Published![/bold green]")
        if result.get("url"):
            console.print(f"[link]{result['url']}[/link]")
        console.print(f"[dim]Post ID: {result['post_id']}[/dim]")
    else:
        console.print(f"[red]❌ Failed: {result['error']}[/red]")


# ─── HISTORY ──────────────────────────────────────────────────────────────────


@linkedin_cmds.command()
@click.option("--limit", "-n", default=10, help="Number of records to show.")
def history(limit: int) -> None:
    """Show LinkedIn publish history (audit log)."""
    from cortex.darknet.linkedin_ledger import LinkedInLedger

    ledger = LinkedInLedger(DEFAULT_DB_PATH)
    records = ledger.fetch_history(limit)

    if not records:
        console.print("[yellow]No publish history found.[/yellow]")
        return

    table = Table(
        title="LinkedIn Publish Ledger",
        border_style="bright_black",
        header_style="bold cyan",
    )
    table.add_column("Hash", style="dim", width=10)
    table.add_column("Title", max_width=35)
    table.add_column("Status", width=8)
    table.add_column("Mode", width=8)
    table.add_column("Date", width=17)
    table.add_column("Post URL", max_width=40)

    for r in records:
        status = "[green]✅[/green]" if r.success else "[red]❌[/red]"
        mode = "[dim]dry[/dim]" if r.dry_run else "[bold]LIVE[/bold]"
        dt = datetime.fromtimestamp(r.published_at).strftime("%Y-%m-%d %H:%M")
        url_text = f"[link={r.post_url}]{r.post_url[:38]}[/link]" if r.post_url else "[dim]—[/dim]"
        table.add_row(r.id[:10], r.title[:35], status, mode, dt, url_text)

    console.print(table)


# ─── Register ─────────────────────────────────────────────────────────────────


def _show_preview(post, content_hash: str, dry_run: bool, actor_urn: str) -> None:
    """Rich preview panel of the post before sending."""
    mode_label = (
        "[yellow]DRY-RUN PREVIEW[/yellow]" if dry_run else "[bold red]LIVE PUBLISH[/bold red]"
    )
    actor_label = actor_urn or "unresolved (preview only)"
    content = (
        f"{mode_label}\n\n"
        f"[bold]Actor:[/bold]     {actor_label}\n"
        f"[bold]Title:[/bold]     {post.title}\n"
        f"[bold]URL:[/bold]       {post.article_url}\n"
        f"[bold]Description:[/bold] {post.description}\n"
        f"[bold]Hash:[/bold]      {content_hash}\n"
        f"[bold]Git SHA:[/bold]   {post.git_sha}\n\n"
        f"[bold]Commentary:[/bold]\n[white]"
        f"{post.commentary[:500]}"
        f"{'...' if len(post.commentary) > 500 else ''}[/white]"
    )
    console.print(Panel(content, title="LinkedIn Post", border_style="blue", expand=False))


cli.add_command(linkedin_cmds)
