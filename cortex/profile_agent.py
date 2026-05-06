"""GitHub profile README projection backed by CORTEX memory and ledger.

This module keeps the agency boundary explicit: CORTEX stores and verifies the
agent state, while the GitHub profile README receives only a bounded public
projection.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from cortex.config import DEFAULT_DB_PATH
from cortex.memory.temporal import now_iso
from cortex.utils.canonical import compute_tx_hash, compute_tx_hash_v1

README_BLOCK_START = "<!-- CORTEX-PROFILE-AGENT:START -->"
README_BLOCK_END = "<!-- CORTEX-PROFILE-AGENT:END -->"
DEFAULT_STATUS_SVG_PATH = "assets/cortex-profile-agent.svg"
DEFAULT_STATUS_JSON_PATH = "assets/cortex-profile-agent.status.json"


@dataclass(frozen=True)
class LedgerProjection:
    """Public, non-sensitive ledger verification summary."""

    valid: bool
    tx_checked: int
    roots_checked: int = 0
    latest_hash: str | None = None
    violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProfileProjection:
    """Bounded public state rendered into the profile README."""

    agent_id: str
    generated_at: str
    profile_repo: str
    source_repo: str
    project: str
    tenant_id: str
    fact_id: int
    ledger: LedgerProjection
    profile_commit: str | None = None

    def public_dict(self) -> dict[str, Any]:
        """Return the serializable projection safe for public output."""
        return asdict(self)


def replace_managed_block(
    readme_text: str,
    rendered_block: str,
    *,
    start_marker: str = README_BLOCK_START,
    end_marker: str = README_BLOCK_END,
) -> str:
    """Replace or append the managed README block."""
    block = f"{start_marker}\n{rendered_block.rstrip()}\n{end_marker}"
    start = readme_text.find(start_marker)
    end = readme_text.find(end_marker)

    if start == -1 and end == -1:
        separator = "\n\n" if readme_text and not readme_text.endswith("\n\n") else ""
        return f"{readme_text}{separator}{block}\n"

    if start == -1 or end == -1 or end < start:
        raise ValueError("README contains an incomplete CORTEX profile-agent block")

    end += len(end_marker)
    return f"{readme_text[:start]}{block}{readme_text[end:]}"


def render_public_block(
    projection: ProfileProjection,
    *,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
) -> str:
    """Render a polished README console from public aggregate state only."""
    status = "VALID" if projection.ledger.valid else "ATTENTION_REQUIRED"
    status_color = "2ea44f" if projection.ledger.valid else "d73a49"
    status_label = "verified" if projection.ledger.valid else "attention"
    latest_hash = projection.ledger.latest_hash or "GENESIS"
    short_hash = latest_hash[:16] if latest_hash != "GENESIS" else latest_hash
    profile_commit = projection.profile_commit[:12] if projection.profile_commit else "unknown"
    tx_checked = str(projection.ledger.tx_checked)
    fact_id = f"#{projection.fact_id}"
    public_digest = public_status_digest(
        projection,
        status_svg_path=status_svg_path,
        status_json_path=status_json_path,
    )[:16]

    lines = [
        '<div align="center">',
        "",
        "### CORTEX Live Agent Surface",
        "",
    ]
    if status_svg_path:
        lines.extend(
            [
                f'<img src="{status_svg_path}" '
                'alt="CORTEX profile agent status panel" width="100%">',
                "",
            ]
        )

    lines.extend(
        [
            f"[![Ledger]({_badge_url('ledger', status_label, status_color)})]"
        "(https://github.com/borjamoskv/Cortex-Persist) "
        f"![Transactions]({_badge_url('tx checked', tx_checked, '0969da')}) "
        f"![Memory]({_badge_url('memory', 'CORTEX', '6f42c1')}) "
        f"![Boundary]({_badge_url('privacy boundary', 'redacted', '57606a')})",
        "",
        "**Wake -> Guard -> Store -> Hash -> Verify -> Project**",
        "",
        "</div>",
        "",
        "| Layer | Public Signal |",
        "|---|---|",
        f"| Runtime | `{projection.agent_id}` |",
        f"| Memory admission | `CortexEngine.store(...) -> fact {fact_id}` |",
        f"| Ledger | `{status}` over `{tx_checked}` checked transaction(s) |",
        f"| Hash anchor | `{short_hash}` |",
        f"| Public digest | `{public_digest}` |",
        f"| Profile commit | `{profile_commit}` |",
        f"| Generated | `{projection.generated_at}` |",
        "",
        "<details>",
        "<summary>Public evidence packet</summary>",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Profile repo | `{projection.profile_repo}` |",
        f"| Source repo | `{projection.source_repo}` |",
        f"| CORTEX project | `{projection.project}` |",
        f"| Tenant scope | `{projection.tenant_id}` |",
        f"| Last public fact | `{fact_id}` |",
        f"| Merkle roots checked | `{projection.ledger.roots_checked}` |",
        f"| Public status JSON | `{status_json_path or 'disabled'}` |",
        "",
        "This is a public projection only. Raw memory, prompts, tenant payloads, secrets, and "
        "private ledger details stay outside the README.",
        "",
        "</details>",
        ]
    )

    if projection.ledger.violations:
        lines.extend(
            [
                "",
                "Integrity findings are present in the private CORTEX audit trail. "
                "This public panel intentionally exposes only aggregate status.",
            ]
        )

    return "\n".join(lines)


def _badge_url(label: str, message: str, color: str) -> str:
    """Build a shields.io badge URL with URL-safe path segments."""
    return (
        "https://img.shields.io/badge/"
        f"{quote(label, safe='')}-{quote(message, safe='')}-{quote(color, safe='')}"
        "?style=for-the-badge"
    )


def render_status_json(
    projection: ProfileProjection,
    *,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
) -> str:
    """Render the public machine-readable status contract."""
    latest_hash = projection.ledger.latest_hash or "GENESIS"
    payload = {
        "schema_version": 1,
        "generated_at": projection.generated_at,
        "agent": {
            "id": projection.agent_id,
            "runtime_boundary": "cortex-profile-agent",
            "memory_admission": "CortexEngine.store",
        },
        "repositories": {
            "profile": projection.profile_repo,
            "source": projection.source_repo,
            "profile_commit": projection.profile_commit,
        },
        "cortex": {
            "project": projection.project,
            "tenant_scope": projection.tenant_id,
            "last_public_fact_id": projection.fact_id,
        },
        "ledger": {
            "valid": projection.ledger.valid,
            "status": "VALID" if projection.ledger.valid else "ATTENTION_REQUIRED",
            "transactions_checked": projection.ledger.tx_checked,
            "merkle_roots_checked": projection.ledger.roots_checked,
            "latest_hash": latest_hash,
            "latest_hash_short": latest_hash[:18] if latest_hash != "GENESIS" else latest_hash,
            "violations_public": list(projection.ledger.violations),
        },
        "artifacts": {
            "readme_block_markers": [README_BLOCK_START, README_BLOCK_END],
            "status_svg": status_svg_path,
            "status_json": status_json_path,
        },
        "privacy_boundary": {
            "raw_memory_published": False,
            "prompts_published": False,
            "tenant_payloads_published": False,
            "secrets_published": False,
            "public_projection_only": True,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def public_status_digest(
    projection: ProfileProjection,
    *,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
) -> str:
    """Return a SHA-256 digest of the public status JSON contract."""
    rendered = render_status_json(
        projection,
        status_svg_path=status_svg_path,
        status_json_path=status_json_path,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def render_status_svg(
    projection: ProfileProjection,
    *,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
) -> str:
    """Render a static SVG status panel for GitHub profile display."""
    status = "VERIFIED" if projection.ledger.valid else "ATTENTION"
    status_color = "#2da44e" if projection.ledger.valid else "#cf222e"
    latest_hash = projection.ledger.latest_hash or "GENESIS"
    short_hash = latest_hash[:18] if latest_hash != "GENESIS" else latest_hash
    profile_commit = projection.profile_commit[:12] if projection.profile_commit else "unknown"
    tx_checked = str(projection.ledger.tx_checked)
    roots_checked = str(projection.ledger.roots_checked)
    public_digest = public_status_digest(
        projection,
        status_svg_path=status_svg_path,
        status_json_path=status_json_path,
    )[:16]

    def esc(value: object) -> str:
        return html.escape(str(value), quote=True)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="360" viewBox="0 0 1100 360" role="img" aria-labelledby="title desc">
  <title id="title">CORTEX profile agent status</title>
  <desc id="desc">Public CORTEX-backed GitHub profile agent projection with ledger status {esc(status)}.</desc>
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d1117"/>
      <stop offset="0.52" stop-color="#111827"/>
      <stop offset="1" stop-color="#172033"/>
    </linearGradient>
    <linearGradient id="signal" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#2da44e"/>
      <stop offset="0.48" stop-color="#0969da"/>
      <stop offset="1" stop-color="#bf8700"/>
    </linearGradient>
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="1100" height="360" rx="24" fill="url(#panel)"/>
  <path d="M36 78 H1064 M36 152 H1064 M36 226 H1064 M36 300 H1064" stroke="#30363d" stroke-width="1"/>
  <path d="M152 32 V328 M334 32 V328 M516 32 V328 M698 32 V328 M880 32 V328" stroke="#21262d" stroke-width="1"/>
  <rect x="28" y="28" width="1044" height="304" rx="18" fill="none" stroke="#30363d" stroke-width="1.5"/>
  <rect x="52" y="54" width="234" height="48" rx="12" fill="#161b22" stroke="#30363d"/>
  <circle cx="78" cy="78" r="8" fill="{status_color}" filter="url(#softGlow)"/>
  <text x="96" y="84" fill="#f0f6fc" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="18" font-weight="700">CORTEX LIVE SURFACE</text>
  <text x="52" y="136" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13">bounded public projection</text>
  <text x="52" y="166" fill="#f0f6fc" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="28" font-weight="700">{esc(projection.agent_id)}</text>
  <text x="52" y="196" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="14">Wake - Guard - Store - Hash - Verify - Project</text>
  <rect x="52" y="230" width="150" height="54" rx="12" fill="#0d1117" stroke="#30363d"/>
  <text x="70" y="252" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12">LEDGER</text>
  <text x="70" y="275" fill="{status_color}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20" font-weight="700">{status}</text>
  <rect x="218" y="230" width="150" height="54" rx="12" fill="#0d1117" stroke="#30363d"/>
  <text x="236" y="252" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12">TX CHECKED</text>
  <text x="236" y="275" fill="#58a6ff" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20" font-weight="700">{esc(tx_checked)}</text>
  <rect x="384" y="230" width="150" height="54" rx="12" fill="#0d1117" stroke="#30363d"/>
  <text x="402" y="252" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12">FACT</text>
  <text x="402" y="275" fill="#d2a8ff" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20" font-weight="700">#{projection.fact_id}</text>
  <g transform="translate(604 64)">
    <rect x="0" y="0" width="418" height="198" rx="16" fill="#0d1117" stroke="#30363d"/>
    <text x="24" y="36" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12">HASH CHAIN</text>
    <line x1="46" y1="88" x2="356" y2="88" stroke="url(#signal)" stroke-width="5" stroke-linecap="round"/>
    <circle cx="46" cy="88" r="15" fill="#2da44e"/>
    <circle cx="150" cy="88" r="15" fill="#0969da"/>
    <circle cx="254" cy="88" r="15" fill="#6f42c1"/>
    <circle cx="356" cy="88" r="15" fill="#bf8700"/>
    <text x="24" y="146" fill="#f0f6fc" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="18">anchor {esc(short_hash)}</text>
    <text x="24" y="174" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13">commit {esc(profile_commit)} | roots {esc(roots_checked)} | digest {esc(public_digest)}</text>
  </g>
  <text x="52" y="318" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="12">raw memory, prompts, tenant payloads, and secrets are not published</text>
</svg>
"""


def write_status_svg(
    repo_path: str | Path,
    projection: ProfileProjection,
    *,
    asset_path: str = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
    dry_run: bool = False,
) -> Path:
    """Write the static public status SVG into the profile repository."""
    output_path = Path(repo_path).expanduser().resolve() / asset_path
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_status_svg(
                projection,
                status_svg_path=asset_path,
                status_json_path=status_json_path,
            ),
            encoding="utf-8",
        )
    return output_path


def write_status_json(
    repo_path: str | Path,
    projection: ProfileProjection,
    *,
    asset_path: str = DEFAULT_STATUS_JSON_PATH,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    dry_run: bool = False,
) -> Path:
    """Write the public machine-readable status contract into the profile repo."""
    output_path = Path(repo_path).expanduser().resolve() / asset_path
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_status_json(
                projection,
                status_svg_path=status_svg_path,
                status_json_path=asset_path,
            ),
            encoding="utf-8",
        )
    return output_path


def verify_transaction_chain(db_path: str | Path, tenant_id: str | None = None) -> LedgerProjection:
    """Verify the CORTEX transaction hash chain from a read-only SQLite view."""
    path = Path(db_path).expanduser()
    if not path.exists():
        return LedgerProjection(valid=True, tx_checked=0, latest_hash="GENESIS")

    uri = f"file:{path}?mode=ro"
    violations: list[str] = []
    tx_checked = 0
    latest_hash: str | None = "GENESIS"
    expected_prev_by_tenant: dict[str, str] = {}

    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transactions'"
        ).fetchone()
        if table_exists is None:
            return LedgerProjection(valid=True, tx_checked=0, latest_hash="GENESIS")

        if tenant_id is None:
            cursor = conn.execute(
                "SELECT id, tenant_id, project, action, detail, prev_hash, hash, timestamp "
                "FROM transactions ORDER BY id"
            )
        else:
            cursor = conn.execute(
                "SELECT id, tenant_id, project, action, detail, prev_hash, hash, timestamp "
                "FROM transactions WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            )

        for row in cursor:
            tx_checked += 1
            tx_tenant = row["tenant_id"] or "default"
            expected_prev = expected_prev_by_tenant.get(tx_tenant, "GENESIS")
            prev_hash = row["prev_hash"]
            stored_hash = row["hash"]
            latest_hash = stored_hash

            if prev_hash != expected_prev:
                violations.append(
                    f"CHAIN_BREAK tx={row['id']} expected={expected_prev} actual={prev_hash}"
                )

            computed = {
                compute_tx_hash(
                    prev_hash,
                    row["project"],
                    row["action"],
                    row["detail"],
                    row["timestamp"],
                    tenant_id=tx_tenant,
                ),
                compute_tx_hash(
                    prev_hash,
                    row["project"],
                    row["action"],
                    row["detail"],
                    row["timestamp"],
                ),
                compute_tx_hash_v1(
                    prev_hash,
                    row["project"],
                    row["action"],
                    row["detail"],
                    row["timestamp"],
                ),
            }
            if stored_hash not in computed:
                violations.append(f"TAMPER_DETECTED tx={row['id']}")

            expected_prev_by_tenant[tx_tenant] = stored_hash
    finally:
        conn.close()

    return LedgerProjection(
        valid=not violations,
        tx_checked=tx_checked,
        latest_hash=latest_hash,
        violations=tuple(violations[:10]),
    )


async def persist_profile_heartbeat(
    *,
    db_path: str | Path,
    profile_repo: str,
    source_repo: str,
    project: str,
    tenant_id: str,
    agent_id: str,
    profile_commit: str | None,
) -> int:
    """Persist a public-profile heartbeat through the canonical CORTEX store path."""
    from cortex.engine import CortexEngine

    generated_at = now_iso()
    content = (
        f"Profile projection heartbeat generated at {generated_at}. "
        "Only aggregate public ledger status is intended for README publication; "
        "raw private state remains unpublished."
    )
    meta = {
        "public_projection": True,
        "profile_repo": profile_repo,
        "source_repo": source_repo,
        "profile_commit": profile_commit,
        "generated_at": generated_at,
    }

    engine = CortexEngine(db_path=db_path, auto_embed=False)
    try:
        await engine.init_db()
        return await engine.store(
            project=project,
            content=content,
            tenant_id=tenant_id,
            fact_type="bridge",
            tags=["github-profile", "readme", "public-projection"],
            confidence="C4",
            source=f"agent:{agent_id}",
            meta=meta,
        )
    finally:
        await engine.close()


def read_git_commit(repo_path: str | Path) -> str | None:
    """Return HEAD commit for a local git repo, if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    commit = result.stdout.strip()
    return commit or None


async def run_profile_projection(
    *,
    profile_repo_path: str | Path,
    db_path: str | Path,
    profile_repo: str,
    source_repo: str,
    project: str,
    tenant_id: str,
    agent_id: str,
    status_svg_path: str | None = DEFAULT_STATUS_SVG_PATH,
    status_json_path: str | None = DEFAULT_STATUS_JSON_PATH,
    dry_run: bool = False,
) -> ProfileProjection:
    """Persist a heartbeat, verify CORTEX, and update the profile README block."""
    repo_path = Path(profile_repo_path).expanduser().resolve()
    readme_path = repo_path / "README.md"
    if not readme_path.exists():
        raise FileNotFoundError(f"README.md not found in profile repo: {repo_path}")

    profile_commit = read_git_commit(repo_path)
    fact_id = await persist_profile_heartbeat(
        db_path=db_path,
        profile_repo=profile_repo,
        source_repo=source_repo,
        project=project,
        tenant_id=tenant_id,
        agent_id=agent_id,
        profile_commit=profile_commit,
    )
    ledger = verify_transaction_chain(db_path, tenant_id=tenant_id)
    projection = ProfileProjection(
        agent_id=agent_id,
        generated_at=now_iso(),
        profile_repo=profile_repo,
        source_repo=source_repo,
        project=project,
        tenant_id=tenant_id,
        fact_id=fact_id,
        ledger=ledger,
        profile_commit=profile_commit,
    )

    current = readme_path.read_text(encoding="utf-8")
    if status_svg_path:
        write_status_svg(
            repo_path,
            projection,
            asset_path=status_svg_path,
            status_json_path=status_json_path,
            dry_run=dry_run,
        )
    if status_json_path:
        write_status_json(
            repo_path,
            projection,
            asset_path=status_json_path,
            status_svg_path=status_svg_path,
            dry_run=dry_run,
        )
    updated = replace_managed_block(
        current,
        render_public_block(
            projection,
            status_svg_path=status_svg_path,
            status_json_path=status_json_path,
        ),
    )
    if not dry_run and updated != current:
        readme_path.write_text(updated, encoding="utf-8")
    return projection


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the profile-agent CLI parser."""
    parser = argparse.ArgumentParser(
        description="Update a GitHub profile README from CORTEX memory and ledger state."
    )
    parser.add_argument("--profile-repo-path", default=".", help="Local borjamoskv profile repo")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="CORTEX SQLite database path")
    parser.add_argument("--profile-repo", default="borjamoskv/borjamoskv")
    parser.add_argument("--source-repo", default="borjamoskv/Cortex-Persist")
    parser.add_argument("--project", default="github-profile-agent")
    parser.add_argument("--tenant", default="public-profile")
    parser.add_argument("--agent-id", default="cortex-profile-agent")
    parser.add_argument(
        "--status-svg-path",
        default=DEFAULT_STATUS_SVG_PATH,
        help="Profile-repo relative SVG status card path. Use --no-status-svg to disable.",
    )
    parser.add_argument(
        "--status-json-path",
        default=DEFAULT_STATUS_JSON_PATH,
        help="Profile-repo relative public status JSON path. Use --no-status-json to disable.",
    )
    parser.add_argument("--no-status-svg", action="store_true", help="Do not write or reference SVG")
    parser.add_argument("--no-status-json", action="store_true", help="Do not write status JSON")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit the public projection as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    projection = asyncio.run(
        run_profile_projection(
            profile_repo_path=args.profile_repo_path,
            db_path=args.db,
            profile_repo=args.profile_repo,
            source_repo=args.source_repo,
            project=args.project,
            tenant_id=args.tenant,
            agent_id=args.agent_id,
            status_svg_path=None if args.no_status_svg else args.status_svg_path,
            status_json_path=None if args.no_status_json else args.status_json_path,
            dry_run=args.dry_run,
        )
    )
    if args.json:
        sys.stdout.write(json.dumps(projection.public_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_public_block(projection))
        sys.stdout.write("\n")
    return 0 if projection.ledger.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
