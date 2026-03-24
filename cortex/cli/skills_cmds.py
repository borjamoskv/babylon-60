"""CLI commands for bundled and external skills."""

from __future__ import annotations

import json
from typing import Any

import click

from cortex.cli.common import DEFAULT_DB, _run_async, close_engine_sync, get_engine
from cortex.swarm.actuators.skill import (
    SkillActuator,
    build_canonical_kpi_snapshot,
    extract_canonical_kpi_snapshot_record,
    extract_canonical_metrics,
)
from cortex.swarm.discovery import SkillMetadata, SkillRegistry


def _get_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.scan()
    return registry


def _resolve_skill(registry: SkillRegistry, skill_name: str) -> SkillMetadata | None:
    if skill_name in registry.skills:
        return registry.skills[skill_name]

    lowered = skill_name.lower()
    for name, metadata in registry.skills.items():
        if name.lower() == lowered:
            return metadata
    return None


@click.group("skills")
def skills_cmds() -> None:
    """Inspect and run skill metadata from the local skill registry."""


@skills_cmds.command("list")
@click.option("--category", help="Filter by category")
@click.option("--kpi-only", is_flag=True, help="Only include skills with canonical KPI values")
@click.option("--json-output", is_flag=True, help="Render as JSON")
def list_skills(category: str | None, kpi_only: bool, json_output: bool) -> None:
    """List discoverable skills."""
    registry = _get_registry()
    skills = list(registry.skills.values())

    if category:
        skills = [skill for skill in skills if skill.category == category]
    if kpi_only:
        skills = [skill for skill in skills if extract_canonical_metrics(skill)]

    payload: list[dict[str, Any]] = []
    for skill in skills:
        payload.append(
            {
                "name": skill.name,
                "category": skill.category,
                "trigger": skill.trigger,
                "has_canonical_kpi": bool(extract_canonical_metrics(skill)),
            }
        )

    if json_output:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    for item in payload:
        click.echo(
            f"{item['name']}\t{item['category']}\t{item['trigger']}\t"
            f"kpi={str(item['has_canonical_kpi']).lower()}"
        )


@skills_cmds.command("kpi")
@click.argument("skill_name")
@click.option("--json-output", is_flag=True, help="Render as JSON")
def skill_kpi(skill_name: str, json_output: bool) -> None:
    """Print canonical KPI values for a skill."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise click.ClickException(f"Unknown skill: {skill_name}")

    response = _run_async(SkillActuator(skill).execute("report canonical kpi", {}))
    if response["metadata"].get("mode") != "canonical_kpi":
        raise click.ClickException(f"Skill '{skill.name}' does not expose canonical KPIs")

    if json_output:
        payload = {
            "skill_name": response["metadata"]["skill_name"],
            "trigger": response["metadata"]["trigger"],
            "metrics": response["metadata"]["metrics"],
        }
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(response["content"])


@skills_cmds.command("snapshot")
@click.argument("skill_name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--project", default="metrics", help="Project namespace for the snapshot")
@click.option("--fact-type", default="knowledge", help="Fact type to persist")
@click.option("--source", default="cli:skills", help="Source label for the stored fact")
@click.option("--tag", "tags", multiple=True, help="Extra tag to attach")
@click.option("--json-output", is_flag=True, help="Render as JSON")
def snapshot_skill(
    skill_name: str,
    db: str,
    project: str,
    fact_type: str,
    source: str,
    tags: tuple[str, ...],
    json_output: bool,
) -> None:
    """Persist a canonical KPI snapshot as a local fact."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise click.ClickException(f"Unknown skill: {skill_name}")

    if not extract_canonical_metrics(skill):
        raise click.ClickException(f"Skill '{skill.name}' does not expose canonical KPIs")

    snapshot = build_canonical_kpi_snapshot(skill)
    merged_tags = list(dict.fromkeys(["kpi", "skill", skill.name, *tags]))
    meta = {
        "skill_name": skill.name,
        "trigger": skill.trigger,
        "captured_at": snapshot["captured_at"],
        "metrics": snapshot["metrics"],
    }

    engine = get_engine(db)
    try:
        fact_id = engine.store_sync(
            project=project,
            content=snapshot["content"],
            fact_type=fact_type,
            tags=merged_tags,
            source=source,
            meta=meta,
        )
    finally:
        close_engine_sync(engine)

    payload = {
        "fact_id": fact_id,
        "skill_name": skill.name,
        "project": project,
        "metrics": snapshot["metrics"],
        "captured_at": snapshot["captured_at"],
    }

    if json_output:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(
        f"Stored KPI snapshot for {skill.name} as fact #{fact_id} in project '{project}'"
    )


@skills_cmds.command("history")
@click.argument("skill_name")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--project", default="metrics", help="Project namespace for KPI snapshots")
@click.option("--limit", default=20, type=click.IntRange(1, 200), help="Max snapshots to show")
@click.option("--json-output", is_flag=True, help="Render as JSON")
def skill_history(
    skill_name: str,
    db: str,
    project: str,
    limit: int,
    json_output: bool,
) -> None:
    """List persisted canonical KPI snapshots for a skill."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise click.ClickException(f"Unknown skill: {skill_name}")

    if not extract_canonical_metrics(skill):
        raise click.ClickException(f"Skill '{skill.name}' does not expose canonical KPIs")

    engine = get_engine(db)
    try:
        facts = _run_async(engine.history(project=project))
    finally:
        close_engine_sync(engine)

    payload = [
        record
        for fact in facts
        if (record := extract_canonical_kpi_snapshot_record(fact, skill.name)) is not None
    ][:limit]

    if json_output:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    if not payload:
        click.echo(f"No KPI snapshots found for {skill.name} in project '{project}'")
        return

    for item in payload:
        metrics = ", ".join(
            f"{metric_name}={metric_value}" for metric_name, metric_value in item["metrics"].items()
        )
        click.echo(
            f"{item['captured_at']}\tfact={item['fact_id']}\tproject={item['project']}\t{metrics}"
        )
