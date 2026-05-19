#!/usr/bin/env python3
"""influencer_tracker_cli.py — CLI for InfluencerTrackerAgent.

C5-REAL execution only. No simulations.

Usage:
    python scripts/influencer_tracker_cli.py seed
    python scripts/influencer_tracker_cli.py list [--confidence C5-REAL|C4]
    python scripts/influencer_tracker_cli.py get "El Xokas"
    python scripts/influencer_tracker_cli.py upsert --name "Borja" --email "borja@example.com" --source manual --confidence C5-REAL
    python scripts/influencer_tracker_cli.py delete "Borja"
    python scripts/influencer_tracker_cli.py stats
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is importable when run directly
_ROOT = Path(__file__).parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cortex.agents.builtins.influencer_tracker_agent import (
    InfluencerContact,
    InfluencerRepository,
)

try:
    from rich.console import Console
    from rich.table import Table

    _RICH = True
except ImportError:
    _RICH = False

_DB_PATH = _ROOT / "influencers.db"
_CSV_PATH = _ROOT / "influencers_contacts.csv"

console = Console(highlight=False) if _RICH else None


# ── Render helpers ─────────────────────────────────────────────────────────────


def _confidence_color(c: str) -> str:
    return {
        "C5-REAL": "bold green",
        "C4": "bold yellow",
        "C3": "yellow",
        "C2": "dim",
        "C1": "dim red",
    }.get(c, "white")


def _print_contacts(contacts: list[InfluencerContact]) -> None:
    if _RICH and console:
        table = Table(
            title=f"[bold cyan]INFLUENCER CONTACTS[/] — {len(contacts)} records",
            style="dim",
            header_style="bold magenta",
            border_style="bright_black",
            show_lines=True,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("NAME", style="bold white", min_width=16)
        table.add_column("EMAIL", style="cyan", min_width=28)
        table.add_column("SOURCE", style="dim white", min_width=20)
        table.add_column("CONFIDENCE", min_width=10)

        for i, c in enumerate(contacts, 1):
            conf_style = _confidence_color(c.confidence)
            table.add_row(
                str(i),
                c.name,
                c.email,
                c.source_type,
                f"[{conf_style}]{c.confidence}[/]",
            )
        console.print(table)
    else:
        print(f"{'#':<4} {'NAME':<20} {'EMAIL':<35} {'SOURCE':<25} {'CONF'}")
        print("-" * 100)
        for i, c in enumerate(contacts, 1):
            print(f"{i:<4} {c.name:<20} {c.email:<35} {c.source_type:<25} {c.confidence}")


def _info(msg: str) -> None:
    if _RICH and console:
        console.print(f"[bold green]✓[/] {msg}")
    else:
        print(f"[OK] {msg}")


def _error(msg: str) -> None:
    if _RICH and console:
        console.print(f"[bold red]✗[/] {msg}")
    else:
        print(f"[ERR] {msg}", file=sys.stderr)


# ── Command handlers ───────────────────────────────────────────────────────────


async def cmd_seed(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv) if args.csv else _CSV_PATH
    if not csv_path.exists():
        _error(f"CSV not found: {csv_path}")
        return 1
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    count = await repo.seed_from_csv(csv_path)
    _info(f"Seeded {count} contacts from {csv_path.name}")
    return 0


async def cmd_list(args: argparse.Namespace) -> int:
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    contacts = await repo.list_all(confidence=args.confidence or None)
    if not contacts:
        _info("No contacts found.")
    else:
        _print_contacts(contacts)
    return 0


async def cmd_get(args: argparse.Namespace) -> int:
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    contact = await repo.get(args.name)
    if contact is None:
        _error(f"Not found: {args.name!r}")
        return 1
    _print_contacts([contact])
    return 0


async def cmd_upsert(args: argparse.Namespace) -> int:
    contact = InfluencerContact(
        name=args.name,
        email=args.email,
        source_type=args.source,
        confidence=args.confidence,
    )
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    await repo.upsert(contact)
    _info(f"Upserted: {contact.name} <{contact.email}>")
    return 0


async def cmd_delete(args: argparse.Namespace) -> int:
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    deleted = await repo.delete(args.name)
    if deleted:
        _info(f"Deleted: {args.name!r}")
    else:
        _error(f"Not found: {args.name!r}")
        return 1
    return 0


async def cmd_stats(args: argparse.Namespace) -> int:  # noqa: ARG001
    repo = InfluencerRepository(_DB_PATH)
    await repo.initialize()
    stats = await repo.stats()
    total = sum(stats.values())

    if _RICH and console:
        table = Table(
            title="[bold cyan]CONFIDENCE DISTRIBUTION[/]",
            header_style="bold magenta",
            border_style="bright_black",
        )
        table.add_column("TIER", style="bold white")
        table.add_column("COUNT", style="cyan", justify="right")
        table.add_column("PCT", style="dim white", justify="right")
        for tier, count in sorted(stats.items()):
            pct = f"{count / total * 100:.1f}%" if total > 0 else "—"
            conf_style = _confidence_color(tier)
            table.add_row(f"[{conf_style}]{tier}[/]", str(count), pct)
        table.add_row("[bold]TOTAL[/]", f"[bold]{total}[/]", "100%")
        console.print(table)
    else:
        print(f"{'TIER':<12} {'COUNT':>6}  {'PCT':>7}")
        print("-" * 30)
        for tier, count in sorted(stats.items()):
            pct = f"{count / total * 100:.1f}%" if total > 0 else "—"
            print(f"{tier:<12} {count:>6}  {pct:>7}")
        print(f"{'TOTAL':<12} {total:>6}")
    return 0


# ── Main ───────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="influencer_tracker",
        description="CORTEX Influencer Contact Tracker — C5-REAL",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # seed
    s_seed = sub.add_parser("seed", help="Load CSV into DB (idempotent)")
    s_seed.add_argument(
        "--csv", default=None, help="Path to CSV (default: influencers_contacts.csv)"
    )

    # list
    s_list = sub.add_parser("list", help="List all contacts")
    s_list.add_argument("--confidence", default=None, choices=["C5-REAL", "C4", "C3", "C2", "C1"])

    # get
    s_get = sub.add_parser("get", help="Fetch contact by name")
    s_get.add_argument("name", help="Influencer name (case-insensitive)")

    # upsert
    s_up = sub.add_parser("upsert", help="Insert or update a contact")
    s_up.add_argument("--name", required=True)
    s_up.add_argument("--email", required=True)
    s_up.add_argument("--source", required=True, dest="source")
    s_up.add_argument("--confidence", required=True, choices=["C5-REAL", "C4", "C3", "C2", "C1"])

    # delete
    s_del = sub.add_parser("delete", help="Delete contact by name")
    s_del.add_argument("name", help="Influencer name")

    # stats
    sub.add_parser("stats", help="Confidence distribution stats")

    return p


_CMD_MAP = {
    "seed": cmd_seed,
    "list": cmd_list,
    "get": cmd_get,
    "upsert": cmd_upsert,
    "delete": cmd_delete,
    "stats": cmd_stats,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handler = _CMD_MAP[args.cmd]
    return asyncio.run(handler(args))


if __name__ == "__main__":
    sys.exit(main())
