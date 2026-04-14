"""CORTEX Health Index — FastAPI routes.

Provides /v1/health/check, /v1/health/report, /v1/health/score,
/v1/health/metrics, /v1/health/prometheus, /v1/health/history
powered by the Health Index engine.
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from cortex.extensions.health import HealthCollector, HealthScorer
from cortex.extensions.health.reporting import build_health_report
from cortex.types.models import (
    HealthHistoryResponse,
    HealthIndexCheckResponse,
    HealthIndexMetricsResponse,
    HealthIndexReportResponse,
    HealthIndexScoreResponse,
    RuntimeHealthGrade,
)

logger = logging.getLogger("cortex.routes.health")

router = APIRouter(prefix="/v1/health", tags=["health-index"])


@router.get("/check", response_model=HealthIndexCheckResponse)
async def health_index_check(request: Request) -> HealthIndexCheckResponse:
    """Quick health check — score, grade, healthy boolean."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    return HealthIndexCheckResponse(
        healthy=hs.score >= 40.0,
        score=round(hs.score, 2),
        grade=cast(RuntimeHealthGrade, hs.grade.letter),
        summary=HealthScorer.summarize(hs),
    )


@router.get("/score", response_model=HealthIndexScoreResponse)
async def health_index_score(request: Request) -> HealthIndexScoreResponse:
    """Numeric score only (0-100)."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    return HealthIndexScoreResponse(
        score=round(hs.score, 2),
        grade=cast(RuntimeHealthGrade, hs.grade.letter),
    )


@router.get("/report", response_model=HealthIndexReportResponse)
async def health_index_report(request: Request) -> HealthIndexReportResponse:
    """Full health report with recommendations and warnings."""
    db_path = _get_db_path(request)
    report = build_health_report(db_path)
    return HealthIndexReportResponse.model_validate(report.to_dict())


@router.get("/metrics", response_model=HealthIndexMetricsResponse)
async def health_index_metrics(request: Request) -> HealthIndexMetricsResponse:
    """Raw metric snapshots for monitoring dashboards."""
    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    return HealthIndexMetricsResponse.model_validate(
        {
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "weight": m.weight,
                    "unit": m.unit,
                    "latency_ms": round(getattr(m, "latency_ms", 0.0), 2),
                    "description": getattr(m, "description", ""),
                    "remediation": getattr(m, "remediation", ""),
                    "collected_at": m.collected_at,
                }
                for m in metrics
            ],
        }
    )


@router.get("/prometheus", response_class=PlainTextResponse)
async def health_index_prometheus(request: Request):
    """Prometheus text exposition format."""
    from cortex.extensions.health.prometheus import export_prometheus

    db_path = _get_db_path(request)
    collector = HealthCollector(db_path=db_path)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)
    content = export_prometheus(hs)
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get("/history", response_model=HealthHistoryResponse)
async def health_index_history(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
) -> HealthHistoryResponse:
    """Persisted health score history."""
    from cortex.extensions.health.trend import TrendDetector

    db_path = _get_db_path(request)
    records = TrendDetector.query_history(db_path, limit=limit)
    return HealthHistoryResponse.model_validate({"history": records, "count": len(records)})


def _get_db_path(request: Request) -> str:
    """Extract DB path from the running engine."""
    try:
        engine = getattr(request.app.state, "engine", None)
        if engine:
            return str(getattr(engine, "_db_path", ""))
    except Exception:  # noqa: BLE001
        logger.debug("Failed to resolve DB path from app state", exc_info=True)
    return ""
