"""Canonical health report builders for routes, SDK, and machine consumers."""

from __future__ import annotations

from typing import Any, Literal

from cortex.extensions.health.collector import CollectorRegistry, HealthCollector
from cortex.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthThresholds,
    MetricSnapshot,
)
from cortex.extensions.health.scorer import HealthScorer
from cortex.extensions.health.trend import TrendDetector

RuntimeStatus = Literal["ok", "degraded", "blocked"]
ComponentStatus = Literal["ok", "degraded", "blocked"]


def collect_health_score(
    db_path: str = "",
    *,
    weights: dict[str, float] | None = None,
    registry: CollectorRegistry | None = None,
) -> HealthScore:
    """Collect live metrics and compute the aggregate health score."""
    collector = HealthCollector(db_path=db_path, registry=registry)
    metrics = collector.collect_all()
    return HealthScorer.score(metrics, weights=weights)


def classify_component_status(
    metric: MetricSnapshot,
    thresholds: HealthThresholds | None = None,
) -> ComponentStatus:
    """Classify one metric using the canonical health thresholds."""
    t = thresholds or HealthThresholds()
    if metric.value < t.critical:
        return "blocked"
    if metric.value < t.degraded:
        return "degraded"
    return "ok"


def build_health_report(
    db_path: str = "",
    *,
    weights: dict[str, float] | None = None,
    registry: CollectorRegistry | None = None,
    history_limit: int | None = None,
) -> HealthReport:
    """Build the full human-readable health report without persisting it."""
    hs = collect_health_score(db_path, weights=weights, registry=registry)
    thresholds = HealthThresholds()

    recommendations: list[str] = []
    warnings: list[str] = []

    for metric in hs.metrics:
        if metric.value < thresholds.critical:
            warnings.append(f"{metric.name}: CRITICAL ({metric.value:.0%})")
        elif metric.value < thresholds.degraded:
            warnings.append(f"{metric.name}: degraded ({metric.value:.0%})")
        elif metric.value < thresholds.improve:
            recommendations.append(f"{metric.name}: could improve ({metric.value:.0%})")

    if hs.grade <= Grade.FAILED:
        warnings.append(
            f"Overall health is FAILED ({hs.grade.letter}) — immediate investigation required"
        )
    elif hs.grade <= Grade.DEGRADED:
        warnings.append(f"Overall health is DEGRADED ({hs.grade.letter})")
    elif hs.grade <= Grade.ACCEPTABLE:
        recommendations.append("Run `cortex compact` to reduce entropy")
    elif hs.grade <= Grade.GOOD:
        recommendations.append("Health is Good — consider ledger verification")

    trend = TrendDetector()
    if db_path:
        trend.load_from_db(db_path, limit=history_limit)
    trend.push(hs.score)
    drift = trend.detect_drift()

    if drift == "degrading":
        warnings.append(f"Health trend is DEGRADING (slope={trend.slope():.2f})")

    return HealthReport(
        score=hs,
        recommendations=recommendations,
        warnings=warnings,
        trend=drift,
        db_path=db_path,
    )


def build_runtime_health_payload(
    db_path: str = "",
    *,
    weights: dict[str, float] | None = None,
    registry: CollectorRegistry | None = None,
    history_limit: int | None = None,
) -> dict[str, Any]:
    """Build the canonical runtime health payload exposed over HTTP/SDK."""
    report = build_health_report(
        db_path,
        weights=weights,
        registry=registry,
        history_limit=history_limit,
    )
    thresholds = HealthThresholds()

    components: dict[str, str] = {}
    component_details: dict[str, dict[str, Any]] = {}
    degraded_features: list[str] = []
    blocked_components: list[str] = []

    for metric in report.score.metrics:
        status = classify_component_status(metric, thresholds)
        components[metric.name] = status
        component_details[metric.name] = {
            "status": status,
            "value": round(metric.value * 100.0, 1),
            "latency_ms": round(metric.latency_ms, 2),
            "description": metric.description,
            "remediation": metric.remediation,
        }
        if status != "ok":
            degraded_features.append(metric.name)
        if status == "blocked":
            blocked_components.append(metric.name)

    runtime_status: RuntimeStatus
    if blocked_components or report.score.grade <= Grade.FAILED:
        runtime_status = "blocked"
    elif report.score.grade <= Grade.ACCEPTABLE or report.warnings or report.trend == "degrading":
        runtime_status = "degraded"
    else:
        runtime_status = "ok"

    return {
        "status": runtime_status,
        "components": components,
        "degraded_features": degraded_features,
        "warnings": report.warnings,
        "score": round(report.score.score, 2),
        "grade": report.score.grade.letter,
        "summary": HealthScorer.summarize(report.score),
        "trend": report.trend,
        "recommendations": report.recommendations,
        "sub_indices": report.score.sub_indices,
        "component_details": component_details,
        "checked_at": report.score.timestamp,
    }
