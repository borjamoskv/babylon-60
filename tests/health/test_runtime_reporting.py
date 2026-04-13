from __future__ import annotations

from pathlib import Path

from cortex.extensions.health.collector import CollectorRegistry
from cortex.extensions.health.models import MetricSnapshot
from cortex.extensions.health.reporting import (
    build_health_report,
    build_runtime_health_payload,
)
from cortex.extensions.health.trend import TrendDetector


class _Collector:
    def __init__(
        self,
        name: str,
        value: float,
        *,
        weight: float = 1.0,
        description: str = "",
        remediation: str = "",
    ) -> None:
        self._name = name
        self._value = value
        self._weight = weight
        self._description = description or f"{name} description"
        self._remediation = remediation or f"{name} remediation"

    @property
    def name(self) -> str:
        return self._name

    @property
    def weight(self) -> float:
        return self._weight

    @property
    def description(self) -> str:
        return self._description

    @property
    def remediation(self) -> str:
        return self._remediation

    def collect(self, db_path: str) -> MetricSnapshot:
        return MetricSnapshot(name=self._name, value=self._value, weight=self._weight)


def _registry(*collectors: _Collector) -> CollectorRegistry:
    registry = CollectorRegistry()
    for collector in collectors:
        registry.register(collector)
    return registry


def test_runtime_health_payload_blocks_on_critical_component() -> None:
    payload = build_runtime_health_payload(
        registry=_registry(
            _Collector("db", 0.2, weight=1.5, remediation="Compact the database"),
            _Collector("ledger", 1.0, weight=1.2),
            _Collector("entropy", 0.9),
            _Collector("facts", 0.9, weight=0.8),
        )
    )

    assert payload["status"] == "blocked"
    assert payload["components"]["db"] == "blocked"
    assert "db" in payload["degraded_features"]
    assert payload["component_details"]["db"]["remediation"] == "Compact the database"
    assert "score" in payload
    assert "grade" in payload
    assert "summary" in payload


def test_build_health_report_uses_history_without_persisting_extra_samples(tmp_path: Path) -> None:
    db_path = str(tmp_path / "health-history.db")
    trend = TrendDetector()
    trend.persist_to_db(db_path, 90.0, "A", timestamp=1000.0)
    trend.persist_to_db(db_path, 80.0, "A", timestamp=2000.0)

    report = build_health_report(
        db_path,
        registry=_registry(
            _Collector("db", 0.6, weight=1.5),
            _Collector("ledger", 0.6, weight=1.2),
            _Collector("entropy", 0.6),
            _Collector("facts", 0.6, weight=0.8),
        ),
    )

    history = TrendDetector.query_history(db_path, limit=10)

    assert report.trend == "degrading"
    assert len(history) == 2
