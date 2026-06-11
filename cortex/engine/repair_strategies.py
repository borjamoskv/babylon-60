# [C5-REAL] Exergy-Maximized
"""Repair Strategy Registry - Deterministic Fix Application for Level 5 Self-Healing.

Each strategy is a pure function: (context, parameters) → RepairResult.
Strategies are registered by anomaly class and executed by the AutoCurativeAgent.

Architecture:
    AutoCurativeEngine (Rust, diagnosis) → RepairStrategy (Python, fix) → Verification

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Protocol

__all__ = [
    "REPAIR_REGISTRY",
    "RepairRegistry",
    "RepairResult",
    "RepairStatus",
    "RepairStrategy",
]

logger = logging.getLogger("cortex.engine.repair")


# ─── Types ────────────────────────────────────────────────────────


class RepairStatus(Enum):
    """Outcome of a repair attempt."""

    SUCCESS = auto()
    PARTIAL = auto()
    FAILED = auto()
    SKIPPED = auto()  # repair was not applicable


@dataclass
class RepairResult:
    """Outcome of a single repair execution."""

    status: RepairStatus
    strategy: str
    target: str
    latency_ms: float
    message: str = ""
    side_effects: list[str] = field(default_factory=list)
    rollback_available: bool = False

    @property
    def succeeded(self) -> bool:
        return self.status in (RepairStatus.SUCCESS, RepairStatus.PARTIAL)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.name,
            "strategy": self.strategy,
            "target": self.target,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "side_effects": self.side_effects,
            "rollback_available": self.rollback_available,
        }


class RepairStrategy(Protocol):
    """Protocol for repair strategies."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult: ...


# ─── Concrete Strategies ──────────────────────────────────────────

from cortex.engine._repair_concrete import (
    InjectTimeoutGuard,
    ForceGcAndReduceBatch,
    ResetPoolAndRetry,
    ExponentialBackoff,
    ProbeAndResetBreaker,
    RestartHeartbeatEmitter,
    TriggerConsolidation,
    SnapshotAndRollback,
    LogAndEscalate,
    ReserializeWithValidation,
)



# ─── Registry ─────────────────────────────────────────────────────


class RepairRegistry:
    """Maps repair strategy names to their implementations.

    Thread-safe, extensible registry. New strategies can be registered
    at runtime for plugin-based healing.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, RepairStrategy] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in repair strategies."""
        self._strategies = {
            "INJECT_TIMEOUT_GUARD": InjectTimeoutGuard(),
            "FORCE_GC_AND_REDUCE_BATCH": ForceGcAndReduceBatch(),
            "RESET_POOL_AND_RETRY": ResetPoolAndRetry(),
            "EXPONENTIAL_BACKOFF": ExponentialBackoff(),
            "PROBE_AND_RESET_BREAKER": ProbeAndResetBreaker(),
            "RESTART_HEARTBEAT_EMITTER": RestartHeartbeatEmitter(),
            "TRIGGER_CONSOLIDATION": TriggerConsolidation(),
            "SNAPSHOT_AND_ROLLBACK": SnapshotAndRollback(),
            "LOG_AND_ESCALATE": LogAndEscalate(),
            "RESERIALIZE_WITH_VALIDATION": ReserializeWithValidation(),
        }

    def register(self, name: str, strategy: RepairStrategy) -> None:
        """Register a custom repair strategy."""
        self._strategies[name] = strategy
        logger.info("[REPAIR] Strategy registered: %s", name)

    def get(self, name: str) -> RepairStrategy | None:
        """Get a repair strategy by name."""
        return self._strategies.get(name)

    async def execute(
        self,
        strategy_name: str,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        """Execute a repair strategy by name."""
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy=strategy_name,
                target=target,
                latency_ms=0.0,
                message=f"Unknown repair strategy: {strategy_name}",
            )

        try:
            return await strategy.execute(target, parameters, context)
        except Exception as e:
            logger.exception("[REPAIR] Strategy %s crashed: %s", strategy_name, e)
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy=strategy_name,
                target=target,
                latency_ms=0.0,
                message=f"Strategy execution crashed: {e}",
            )

    @property
    def available_strategies(self) -> list[str]:
        return list(self._strategies.keys())


# Module-level singleton
REPAIR_REGISTRY = RepairRegistry()
