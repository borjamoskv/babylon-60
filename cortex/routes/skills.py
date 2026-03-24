"""HTTP routes for local skill discovery and canonical KPI exposure."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.swarm.actuators.skill import (
    SkillActuator,
    build_canonical_kpi_snapshot,
    extract_canonical_kpi_snapshot_record,
    extract_canonical_metrics,
)
from cortex.swarm.discovery import SkillMetadata, SkillRegistry

router = APIRouter(prefix="/v1/skills", tags=["skills"])
require_read_permission = require_permission("read")
require_write_permission = require_permission("write")


class SkillSummary(BaseModel):
    """Minimal API view over a discovered skill."""

    name: str
    category: str
    trigger: str
    has_canonical_kpi: bool


class SkillKPIResponse(BaseModel):
    """Canonical KPI payload exposed by a skill."""

    skill_name: str
    trigger: str
    metrics: dict[str, Any]
    content: str


class SkillSnapshotRequest(BaseModel):
    """Request body for persisting a canonical KPI snapshot as a fact."""

    project: str = Field("metrics", min_length=1, max_length=100)
    fact_type: str = Field("knowledge", max_length=20)
    source: str = Field("api:skills", max_length=200)
    tags: list[str] = Field(default_factory=list)
    meta: dict[str, Any] | None = None


class SkillSnapshotResponse(BaseModel):
    """Response after snapshot persistence."""

    fact_id: int
    skill_name: str
    project: str
    metrics: dict[str, Any]
    captured_at: str
    message: str


class SkillSnapshotRecord(BaseModel):
    """Historical canonical KPI snapshot already persisted as a fact."""

    fact_id: int
    skill_name: str
    project: str
    fact_type: str
    source: str
    content: str
    tags: list[str]
    captured_at: str
    created_at: str
    metrics: dict[str, Any]


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


@router.get("", response_model=list[SkillSummary])
async def list_skills(
    category: str | None = Query(default=None),
    kpi_only: bool = Query(default=False),
    _auth: AuthResult = Depends(require_read_permission),
) -> list[SkillSummary]:
    """List discovered skills, optionally filtered to KPI-capable skills."""
    registry = _get_registry()
    skills = list(registry.skills.values())

    if category:
        skills = [skill for skill in skills if skill.category == category]
    if kpi_only:
        skills = [skill for skill in skills if extract_canonical_metrics(skill)]

    return [
        SkillSummary(
            name=skill.name,
            category=skill.category,
            trigger=skill.trigger,
            has_canonical_kpi=bool(extract_canonical_metrics(skill)),
        )
        for skill in skills
    ]


@router.get("/{skill_name}/kpi", response_model=SkillKPIResponse)
async def get_skill_kpi(
    skill_name: str,
    _auth: AuthResult = Depends(require_read_permission),
) -> SkillKPIResponse:
    """Return canonical KPI values declared by a skill."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")

    if not extract_canonical_metrics(skill):
        raise HTTPException(
            status_code=400,
            detail=f"Skill '{skill.name}' does not expose canonical KPIs",
        )

    response = await SkillActuator(skill).execute("report canonical kpi", {})
    return SkillKPIResponse(
        skill_name=response["metadata"]["skill_name"],
        trigger=response["metadata"]["trigger"],
        metrics=response["metadata"]["metrics"],
        content=response["content"],
    )


@router.post("/{skill_name}/snapshot", response_model=SkillSnapshotResponse)
async def create_skill_snapshot(
    skill_name: str,
    req: SkillSnapshotRequest,
    auth: AuthResult = Depends(require_write_permission),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> SkillSnapshotResponse:
    """Persist the current canonical KPI bundle as a fact."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")

    metrics = extract_canonical_metrics(skill)
    if not metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Skill '{skill.name}' does not expose canonical KPIs",
        )

    snapshot = build_canonical_kpi_snapshot(skill)
    metric_map = snapshot["metrics"]
    captured_at = snapshot["captured_at"]
    merged_tags = list(dict.fromkeys(["kpi", "skill", skill.name, *req.tags]))
    merged_meta = {
        "skill_name": skill.name,
        "trigger": skill.trigger,
        "captured_at": captured_at,
        "metrics": metric_map,
        **(req.meta or {}),
    }

    fact_id = await engine.store(
        project=req.project,
        content=snapshot["content"],
        tenant_id=auth.tenant_id,
        fact_type=req.fact_type,
        tags=merged_tags,
        source=req.source,
        meta=merged_meta,
    )

    return SkillSnapshotResponse(
        fact_id=fact_id,
        skill_name=skill.name,
        project=req.project,
        metrics=metric_map,
        captured_at=captured_at,
        message="KPI snapshot stored",
    )


@router.get("/{skill_name}/snapshots", response_model=list[SkillSnapshotRecord])
async def list_skill_snapshots(
    skill_name: str,
    project: str = Query(default="metrics", min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=200),
    auth: AuthResult = Depends(require_read_permission),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> list[SkillSnapshotRecord]:
    """List persisted canonical KPI snapshots for a skill within a project."""
    registry = _get_registry()
    skill = _resolve_skill(registry, skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_name}")

    if not extract_canonical_metrics(skill):
        raise HTTPException(
            status_code=400,
            detail=f"Skill '{skill.name}' does not expose canonical KPIs",
        )

    facts = await engine.history(project=project, tenant_id=auth.tenant_id)
    records: list[SkillSnapshotRecord] = []
    for fact in facts:
        record = extract_canonical_kpi_snapshot_record(fact, skill.name)
        if record is None:
            continue
        records.append(SkillSnapshotRecord(**record))
        if len(records) >= limit:
            break

    return records
