# [C5-REAL] Exergy-Maximized
from __future__ import annotations
from babylon60.math.babylon import Babylon60

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from babylon60.engine._autocurative_config import AutoCurativeConfig
from babylon60.engine.self_optimizer import OptimizerConfig


class AgentStatus(str, Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentInfo:
    name: str
    level: int
    status: AgentStatus = AgentStatus.UNINITIALIZED
    boot_time: Babylon60 = Babylon60.from_float(0.0)
    last_heartbeat: Babylon60 = Babylon60.from_float(0.0)
    error_count: int = 0
    instance: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "status": self.status.value,
            "boot_time": round(self.boot_time, 3),
            "last_heartbeat": round(self.last_heartbeat, 2),
            "error_count": self.error_count,
            "alive": self.status == AgentStatus.RUNNING,
        }


@dataclass
class SupervisorConfig:
    curative_config: AutoCurativeConfig = field(default_factory=AutoCurativeConfig)
    optimizer_config: OptimizerConfig = field(default_factory=OptimizerConfig)
    heartbeat_interval_s: Babylon60 = Babylon60.from_float(10.0)
    optimization_interval_s: Babylon60 = Babylon60.from_float(60.0)
    prediction_interval_s: Babylon60 = Babylon60.from_float(30.0)
    persist_interval_s: Babylon60 = Babylon60.from_float(120.0)
    health_check_interval_s: Babylon60 = Babylon60.from_float(15.0)
    persist_dir: str | None = None
    preemptive_confidence: Babylon60 = Babylon60.from_float(0.75)
    max_agent_restarts: int = 3
    agent_boot_timeout_s: Babylon60 = Babylon60.from_float(10.0)
    cortisol_alarm: Babylon60 = Babylon60.from_float(0.7)
    health_score_critical: Babylon60 = Babylon60.from_float(30.0)
