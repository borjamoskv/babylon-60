"""CORTEX CLI — Health dashboard command.

Rich terminal dashboard showing system health at a glance.
Added to the `cortex health` command group.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, console  # type: ignore[reportAttributeAccessIssue]


@click.command("dashboard")
@click.option("--db", "db_path", default=None, help="DB path override.")
def dashboard(db_path: str | None) -> None:
    """Rich interactive live dashboard for CORTEX Health."""
    from cortex.extensions.health import build_runtime_health_payload
    from cortex.extensions.health.models import Grade

    path = db_path or str(DEFAULT_DB)
    payload = build_runtime_health_payload(path)
    grade = Grade.from_letter(payload["grade"])
    component_details = payload.get("component_details", {})

    # ─── Grade Panel ──────────────────────────────────────
    grade_colors = {
        Grade.SOVEREIGN: "bright_green",
        Grade.EXCELLENT: "green",
        Grade.GOOD: "cyan",
        Grade.ACCEPTABLE: "yellow",
        Grade.DEGRADED: "red",
        Grade.FAILED: "bright_red",
    }
    color = grade_colors.get(grade, "white")

    console.print()
    console.print(
        Panel(
            (
                f"[bold {color}]{grade.emoji} {payload['score']:.1f}/100  "
                f"Grade {payload['grade']}[/]\n"
                f"[dim]status={payload['status']} · trend={payload['trend']}[/]"
            ),
            title="[bold]CORTEX HEALTH INDEX[/]",
            subtitle=f"[dim]{path}[/]",
            border_style=color,
            width=60,
        )
    )

    # ─── Metrics Table ────────────────────────────────────
    table = Table(
        title="Metric Breakdown",
        show_header=True,
        header_style="bold cyan",
        width=84,
    )
    table.add_column("Metric", style="bold", width=10)
    table.add_column("Status", width=10)
    table.add_column("Bar", width=22)
    table.add_column("Value", justify="right", width=7)
    table.add_column("ms", justify="right", style="dim", width=6)
    table.add_column("Detail", width=24)

    severity_rank = {"blocked": 0, "degraded": 1, "ok": 2}
    for name, detail in sorted(
        component_details.items(),
        key=lambda item: (severity_rank.get(str(item[1]["status"]), 99), item[0]),
    ):
        value = float(detail["value"]) / 100.0
        filled = int(value * 20)
        bar = "█" * filled + "░" * (20 - filled)

        if detail["status"] == "blocked":
            val_color = "red"
        elif detail["status"] == "degraded":
            val_color = "yellow"
        elif value >= 0.8:
            val_color = "green"
        else:
            val_color = "cyan"

        table.add_row(
            name.upper(),
            f"[{val_color}]{detail['status']}[/]",
            f"[{val_color}]{bar}[/]",
            f"[{val_color}]{value:.0%}[/]",
            f"{float(detail['latency_ms']):.0f}",
            str(detail["description"])[:30] if detail["description"] else "",
        )

    console.print(table)

    # ─── Sub-Indices ──────────────────────────────────────
    if payload.get("sub_indices"):
        lines = []
        for idx_name, val in payload["sub_indices"].items():
            filled = int(val / 100 * 20)
            bar = "█" * filled + "░" * (20 - filled)
            if val >= 80:
                c = "green"
            elif val >= 50:
                c = "yellow"
            else:
                c = "red"
            lines.append(f"  {idx_name:16s} [{c}]{bar}[/] {val:.1f}/100")
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold]Sub-Indices[/]",
                border_style="blue",
                width=60,
            )
        )

    # ─── Warnings & Recommendations ──────────────────────
    warns = [f"⚠️  {warning}" for warning in payload.get("warnings", [])]
    recs = [f"💡 {rec}" for rec in payload.get("recommendations", [])]
    actions = [
        f"🔧 {name}: {detail['remediation']}"
        for name, detail in component_details.items()
        if detail["status"] != "ok" and detail["remediation"]
    ]

    if warns:
        console.print(
            Panel(
                "\n".join(warns),
                title="[bold red]Warnings[/]",
                border_style="red",
                width=60,
            )
        )

    if recs:
        console.print(
            Panel(
                "\n".join(recs),
                title="[bold yellow]Recommendations[/]",
                border_style="yellow",
                width=60,
            )
        )

    if actions:
        console.print(
            Panel(
                "\n".join(actions),
                title="[bold]Actions[/]",
                border_style="magenta",
                width=60,
            )
        )

    if not warns and not recs:
        console.print(
            Panel(
                "[green]✅ All systems nominal[/]",
                border_style="green",
                width=60,
            )
        )

    console.print()
