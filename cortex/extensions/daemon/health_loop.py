"""Health monitoring loop for moskv-daemon.

Uses sealed Grade enum for comparisons. TrendDetector for drift.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from cortex.extensions.health.collector import HealthCollector
from cortex.extensions.health.models import Grade
from cortex.extensions.health.reporting import classify_component_status
from cortex.extensions.health.scorer import HealthScorer
from cortex.extensions.health.trend import TrendDetector

logger = logging.getLogger("moskv-daemon.health")

DEFAULT_INTERVAL = 300
ALERT_COOLDOWN = 1800
DEGRADE_THRESHOLD = Grade.GOOD  # Alert below Good


def _escape_osascript_string(value: str) -> str:
    """Escape user-controlled text embedded in AppleScript string literals."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class HealthLoop:
    """Daemon loop: autonomous health monitoring.

    Grade transitions use sealed enum comparison.
    TrendDetector tracks drift over time.
    """

    def __init__(
        self,
        db_path: str | Path = "",
        interval: float = DEFAULT_INTERVAL,
        notify_fn: Callable[[str, str], None] | None = None,
    ) -> None:
        self._db_path = str(db_path)
        self._interval = interval
        self._notify_fn = notify_fn
        self._last_grade: Grade | None = None
        self._last_alert: float = 0.0
        self._trend = TrendDetector()

    def tick(self) -> dict | None:
        """Run one health check cycle."""
        try:
            collector = HealthCollector(db_path=self._db_path)
            metrics = collector.collect_all()
            hs = HealthScorer.score(metrics)
            summary = HealthScorer.summarize(hs)

            self._trend.push(hs.score)
            drift = self._trend.detect_drift()

            logger.info(
                "Health tick: %s [trend=%s]",
                summary,
                drift,
            )

            # Grade change detection via enum comparison
            if self._last_grade is not None and hs.grade != self._last_grade:
                self._on_grade_change(
                    self._last_grade,
                    hs.grade,
                    hs.score,
                )

            components: dict[str, str] = {}
            component_details: dict[str, dict[str, object]] = {}
            degraded_features: list[str] = []
            blocked_components: list[str] = []

            for metric in metrics:
                status = classify_component_status(metric)
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

            status = "ok"
            if blocked_components or hs.grade <= Grade.FAILED:
                status = "blocked"
            elif hs.grade < DEGRADE_THRESHOLD or degraded_features or drift == "degrading":
                status = "degraded"

            if status != "ok":
                self._alert_degraded(
                    hs.score,
                    hs.grade,
                    degraded_features or (["trend"] if drift == "degrading" else []),
                )

            self._last_grade = hs.grade

            return {
                "status": status,
                "score": round(hs.score, 2),
                "grade": hs.grade.letter,
                "healthy": hs.healthy,
                "trend": drift,
                "slope": round(self._trend.slope(), 3),
                "components": components,
                "component_details": component_details,
                "degraded_features": degraded_features,
                "metrics": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "status": components[metric.name],
                    }
                    for metric in metrics
                ],
            }

        except Exception as e:  # noqa: BLE001
            logger.warning("Health tick failed: %s", e)
            return None

    def _on_grade_change(
        self,
        old: Grade,
        new: Grade,
        score: float,
    ) -> None:
        """Handle grade transitions via enum ordering."""
        if new < old:
            logger.warning(
                "Health DEGRADED: %s → %s (%.1f)",
                old.letter,
                new.letter,
                score,
            )
            self._send_notification(
                f"⚠️ CORTEX Health: {old.letter} → {new.letter} ({score:.0f}/100)",
                "Health degradation detected.",
            )
        else:
            logger.info(
                "Health IMPROVED: %s → %s (%.1f)",
                old.letter,
                new.letter,
                score,
            )

    def _alert_degraded(
        self,
        score: float,
        grade: Grade,
        degraded_features: list[str],
    ) -> None:
        """Alert on sustained degradation (rate-limited)."""
        now = time.monotonic()
        if now - self._last_alert < ALERT_COOLDOWN:
            return
        self._last_alert = now
        detail = "System health is below threshold."
        if degraded_features:
            preview = ", ".join(degraded_features[:3])
            suffix = "..." if len(degraded_features) > 3 else ""
            detail = f"Degraded components: {preview}{suffix}"
        self._send_notification(
            f"🔴 CORTEX Health: {score:.0f}/100 ({grade.letter})",
            detail,
        )

    def _send_notification(
        self,
        title: str,
        body: str,
    ) -> None:
        """Dispatch notification via callback or macOS."""
        if self._notify_fn:
            try:
                self._notify_fn(title, body)
            except Exception as e:  # noqa: BLE001
                logger.debug("Notification failed: %s", e)
            return
        try:
            safe_title = _escape_osascript_string(title)
            safe_body = _escape_osascript_string(body)
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{safe_body}" with title "{safe_title}"',
                ],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except Exception:  # noqa: BLE001
            logger.debug("macOS notifications unavailable")

    def persist_snapshot(
        self,
        engine: object,
        data: dict,
    ) -> None:
        """Persist health snapshot as a CORTEX fact."""
        try:
            degraded = data.get("degraded_features") or []
            degraded_label = ""
            if degraded:
                degraded_label = f" — degraded: {', '.join(str(item) for item in degraded[:3])}"
            engine.store_sync(  # type: ignore[attr-defined]
                "cortex",
                content=(f"Health snapshot: {data['score']}/100 ({data['grade']}){degraded_label}"),
                fact_type="bridge",
                source="daemon:health",
                tags=["health", "snapshot", data["grade"]],
                meta=data,
                confidence="C5",
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("Health persist failed: %s", e)
