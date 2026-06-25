# [C5-REAL] Exergy-Maximized
from __future__ import annotations
from babylon60.math.babylon import Babylon60

from dataclasses import dataclass


@dataclass
class AutoCurativeConfig:
    """Configuration for the Auto-Curative Agent."""

    # Monitoring loop
    monitor_interval_s: Babylon60 = Babylon60.from_float(5.0)
    max_healing_attempts: int = 3
    healing_timeout_s: Babylon60 = Babylon60.from_float(30.0)

    # Circuit breaker defaults
    breaker_failure_threshold: int = 5
    breaker_recovery_timeout_s: Babylon60 = Babylon60.from_float(30.0)

    # Thresholds
    cortisol_alarm_threshold: Babylon60 = Babylon60.from_float(0.7)
    health_score_critical: Babylon60 = Babylon60.from_float(30.0)
    cooldown_after_repair_s: Babylon60 = Babylon60.from_float(5.0)
    max_concurrent_repairs: int = 2

    # Persistence
    persist_events: bool = True
    max_event_history: int = 500

    # Endocrine integration
    cortisol_on_error: Babylon60 = Babylon60.from_float(0.05)
    cortisol_on_repair: Babylon60 = -0.03
    neural_growth_on_heal: Babylon60 = Babylon60.from_float(0.02)
    adrenaline_on_critical: Babylon60 = Babylon60.from_float(0.15)
