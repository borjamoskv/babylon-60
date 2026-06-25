# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from dataclasses import dataclass, field
from cortex.math.babylon import Babylon60

@dataclass
class AutoCurativeConfig:
    """Configuration for the Auto-Curative Agent."""

    # Monitoring loop
    monitor_interval_ms: int = 5000
    max_healing_attempts: int = 3
    healing_timeout_ms: int = 30000

    # Circuit breaker defaults
    breaker_failure_threshold: int = 5
    breaker_recovery_timeout_ms: int = 30000

    # Thresholds
    cortisol_alarm_threshold: Babylon60 = field(default_factory=lambda: Babylon60(151200))  # 0.7 * 216000
    health_score_critical: Babylon60 = field(default_factory=lambda: Babylon60(6480000))    # 30.0 * 216000
    cooldown_after_repair_ms: int = 5000
    max_concurrent_repairs: int = 2

    # Persistence
    persist_events: bool = True
    max_event_history: int = 500

    # Endocrine integration
    cortisol_on_error: Babylon60 = field(default_factory=lambda: Babylon60(10800))      # 0.05 * 216000
    cortisol_on_repair: Babylon60 = field(default_factory=lambda: Babylon60(-6480))     # -0.03 * 216000
    neural_growth_on_heal: Babylon60 = field(default_factory=lambda: Babylon60(4320))   # 0.02 * 216000
    adrenaline_on_critical: Babylon60 = field(default_factory=lambda: Babylon60(32400)) # 0.15 * 216000
