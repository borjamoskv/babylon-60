"""CORTEX Health — system-wide monitoring and scoring.

Usage::

    from cortex.experimental.extensions.health import HealthCollector, HealthScorer, Grade

    collector = HealthCollector(db_path="~/.cortex/cortex.db")
    metrics = collector.collect_all()
    score = HealthScorer.score(metrics)
    print(score.grade)  # Grade.SOVEREIGN
"""

from cortex.experimental.extensions.health.collector import (
    CollectorRegistry,
    HealthCollector,
    create_default_registry,
)
from cortex.experimental.extensions.health.health_mixin import HealthMixin
from cortex.experimental.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.experimental.extensions.health.invariants import verify_health_system
from cortex.experimental.extensions.health.models import (
    Grade,
    HealthReport,
    HealthScore,
    HealthSLA,
    HealthSLAViolation,
    HealthThresholds,
    MetricSnapshot,
)
from cortex.experimental.extensions.health.scorer import HealthScorer
from cortex.experimental.extensions.health.trend import TrendDetector

try:
    from cortex.experimental.extensions.health.prometheus import export_prometheus

    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    export_prometheus = None  # type: ignore

__all__ = [
    "CollectorRegistry",
    "Grade",
    "HealthCollector",
    "HealthMixin",
    "HealthReport",
    "HealthScore",
    "HealthScorer",
    "HealthSLA",
    "HealthSLAViolation",
    "HealthThresholds",
    "MetricCollectorProtocol",
    "MetricSnapshot",
    "TrendDetector",
    "create_default_registry",
    "export_prometheus",
    "verify_health_system",
]
