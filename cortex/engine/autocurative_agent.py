"""Auto-Curative Agent — Level 5 Self-Healing Daemon.

Unifies the CORTEX self-healing primitives into a single closed-loop daemon:

    ┌──────────────────────────┐
    │   LOOP DE AUTO-CURACIÓN  │
    │                          │
    EJECUTAR ──→ MONITOREAR ──→ ¿ERROR? ──→ SÍ ──→ DIAGNOSTICAR ──→ REPARAR
       ▲                          │                                    │
       │                          NO                                   │
       │                          ▼                                    │
       │                       CONTINUAR                               │
       └───────────────────────────────────────────────────────────────┘

Components integrated:
    - CircuitBreaker: Cascading failure protection
    - HeartbeatEmitter: Health pulse monitoring
    - ReflexionEngine: Dispatch tree self-modification
    - AnomalyHunter: NightShift anomaly detection
    - EndocrineRegistry: Hormonal homeostasis signaling
    - RepairRegistry: Deterministic fix application

The Rust AutoCurativeEngine handles fast-path diagnosis and pattern matching.
Python handles the orchestration loop, strategy execution, and ledger persistence.

Reality Level: C5-REAL
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from cortex.engine.circuit_breaker import CircuitBreaker, CircuitState
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.repair_strategies import (
    REPAIR_REGISTRY,
    RepairResult,
    RepairStatus,
)

__all__ = [
    "AutoCurativeAgent",
    "AutoCurativeConfig",
    "HealingEvent",
    "AgentHealth",
]

logger = logging.getLogger("cortex.engine.autocurative")


# ─── Types ────────────────────────────────────────────────────────


class HealingPhase(str, Enum):
    """Current phase of the self-healing loop."""

    IDLE = "idle"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    DIAGNOSING = "diagnosing"
    REPAIRING = "repairing"
    VERIFYING = "verifying"
    COOLDOWN = "cooldown"


@dataclass
class HealingEvent:
    """Record of a single healing cycle."""

    timestamp_ns: int
    phase: HealingPhase
    error_signature: str
    anomaly_class: str
    subsystem: str
    severity: float
    repair_strategy: str
    repair_result: RepairResult | None
    diagnosis_time_ns: int
    total_cycle_ms: float
    iteration: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "phase": self.phase.value,
            "error_signature": self.error_signature[:200],
            "anomaly_class": self.anomaly_class,
            "subsystem": self.subsystem,
            "severity": self.severity,
            "repair_strategy": self.repair_strategy,
            "repair_result": self.repair_result.to_dict() if self.repair_result else None,
            "diagnosis_time_ns": self.diagnosis_time_ns,
            "total_cycle_ms": self.total_cycle_ms,
            "iteration": self.iteration,
        }


@dataclass
class AgentHealth:
    """Overall health state of the Auto-Curative Agent."""

    status: str  # "healthy" | "degraded" | "critical" | "healing"
    uptime_s: float
    total_errors_detected: int
    total_repairs_attempted: int
    total_repairs_succeeded: int
    active_circuit_breakers: dict[str, str]
    cortisol_level: float
    health_score: float
    recent_events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "uptime_s": round(self.uptime_s, 2),
            "total_errors_detected": self.total_errors_detected,
            "total_repairs_attempted": self.total_repairs_attempted,
            "total_repairs_succeeded": self.total_repairs_succeeded,
            "repair_success_rate": (
                self.total_repairs_succeeded / max(1, self.total_repairs_attempted)
            ),
            "active_circuit_breakers": self.active_circuit_breakers,
            "cortisol_level": round(self.cortisol_level, 4),
            "health_score": round(self.health_score, 2),
            "recent_events_count": len(self.recent_events),
        }


@dataclass
class AutoCurativeConfig:
    """Configuration for the Auto-Curative Agent."""

    # Monitoring loop
    monitor_interval_s: float = 5.0
    max_healing_attempts: int = 3
    healing_timeout_s: float = 30.0

    # Circuit breaker defaults
    breaker_failure_threshold: int = 5
    breaker_recovery_timeout_s: float = 30.0

    # Thresholds
    cortisol_alarm_threshold: float = 0.7
    health_score_critical: float = 30.0
    cooldown_after_repair_s: float = 5.0
    max_concurrent_repairs: int = 2

    # Persistence
    persist_events: bool = True
    max_event_history: int = 500

    # Endocrine integration
    cortisol_on_error: float = 0.05
    cortisol_on_repair: float = -0.03
    neural_growth_on_heal: float = 0.02
    adrenaline_on_critical: float = 0.15


# ─── Auto-Curative Agent ─────────────────────────────────────────


class AutoCurativeAgent:
    """Level 5 Self-Healing Daemon.

    Wraps any async task with automatic error detection, diagnosis,
    repair, and verification. The agent monitors its own execution
    and self-repairs without human intervention.

    Usage:
        agent = AutoCurativeAgent()

        # Option 1: Wrap a single task
        result = await agent.execute_with_healing(
            task=my_async_function,
            subsystem="ledger",
        )

        # Option 2: Run as daemon monitoring engine health
        await agent.start_daemon(engine=cortex_engine)

        # Option 3: Manual error injection for testing
        event = await agent.handle_error(
            error=some_exception,
            subsystem="dispatch",
            context={"dispatch_tree": tree},
        )
    """

    def __init__(
        self,
        config: AutoCurativeConfig | None = None,
        repair_registry: Any | None = None,
    ) -> None:
        self.config = config or AutoCurativeConfig()
        self._registry = repair_registry or REPAIR_REGISTRY
        self._phase = HealingPhase.IDLE
        self._start_time = time.monotonic()
        self._is_running = False
        self._daemon_task: asyncio.Task[None] | None = None

        # Metrics
        self._total_errors = 0
        self._total_repairs = 0
        self._successful_repairs = 0
        self._event_history: deque[HealingEvent] = deque(maxlen=self.config.max_event_history)

        # Circuit breakers per subsystem
        self._breakers: dict[str, CircuitBreaker] = {}

        # Concurrency control
        self._repair_semaphore = asyncio.Semaphore(self.config.max_concurrent_repairs)

        # Rust engine (optional fast-path)
        self._rust_engine: Any = None
        self._try_init_rust_engine()

    def _try_init_rust_engine(self) -> None:
        """Attempt to load the Rust AutoCurativeEngine for fast-path diagnosis."""
        try:
            from cortex_rs import AutoCurativeEngine  # type: ignore[import-untyped]

            self._rust_engine = AutoCurativeEngine(window_size=1000)
            logger.info("[AUTOCURATIVE] Rust fast-path engine loaded")
        except ImportError:
            logger.debug("[AUTOCURATIVE] Rust engine not available — using Python fallback")

    def _get_or_create_breaker(self, subsystem: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a subsystem."""
        if subsystem not in self._breakers:
            self._breakers[subsystem] = CircuitBreaker(
                name=f"autocurative:{subsystem}",
                failure_threshold=self.config.breaker_failure_threshold,
                recovery_timeout=self.config.breaker_recovery_timeout_s,
            )
        return self._breakers[subsystem]

    # ─── Core: Execute with Healing ──────────────────────────────

    async def execute_with_healing(
        self,
        task: Any,
        subsystem: str = "default",
        context: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a task with the full self-healing loop.

        If the task fails, the agent will:
        1. MONITOR — Detect the error
        2. DIAGNOSE — Classify and analyze (Rust fast-path if available)
        3. REPAIR — Apply the appropriate fix strategy
        4. VERIFY — Re-execute to confirm the fix worked

        Returns the task result on success, or raises after max attempts.
        """
        breaker = self._get_or_create_breaker(subsystem)
        ctx = context or {}
        last_error: Exception | None = None

        for attempt in range(self.config.max_healing_attempts):
            cycle_start = time.perf_counter_ns()

            # ─── CHECK: Circuit breaker ────────────────────────
            if breaker.state == CircuitState.OPEN:
                logger.warning(
                    "[AUTOCURATIVE] Circuit breaker OPEN for '%s' — skipping execution",
                    subsystem,
                )
                ENDOCRINE.pulse(
                    HormoneType.ADRENALINE,
                    self.config.adrenaline_on_critical,
                    reason=f"Circuit OPEN: {subsystem}",
                )
                raise RuntimeError(
                    f"AutoCurative: circuit breaker OPEN for '{subsystem}' "
                    f"after {breaker.total_trips} trips"
                )

            # ─── EXECUTE ──────────────────────────────────────
            self._phase = HealingPhase.EXECUTING
            try:
                if asyncio.iscoroutinefunction(task):
                    result = await asyncio.wait_for(
                        task(*args, **kwargs),
                        timeout=self.config.healing_timeout_s,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(task, *args, **kwargs),
                        timeout=self.config.healing_timeout_s,
                    )

                # ─── SUCCESS ──────────────────────────────────
                self._phase = HealingPhase.IDLE
                breaker._on_success()

                if attempt > 0:
                    # Healed after previous failure
                    logger.info(
                        "[AUTOCURATIVE] ✅ Task healed after %d attempt(s) in '%s'",
                        attempt,
                        subsystem,
                    )
                    ENDOCRINE.pulse(
                        HormoneType.NEURAL_GROWTH,
                        self.config.neural_growth_on_heal,
                        reason=f"Self-healed: {subsystem}",
                    )
                    ENDOCRINE.pulse(
                        HormoneType.CORTISOL,
                        self.config.cortisol_on_repair,
                        reason=f"Repair relief: {subsystem}",
                    )

                return result

            except Exception as error:
                last_error = error
                breaker._on_failure()

                # ─── MONITOR (error detected) ─────────────────
                self._phase = HealingPhase.MONITORING
                self._total_errors += 1
                ENDOCRINE.pulse(
                    HormoneType.CORTISOL,
                    self.config.cortisol_on_error,
                    reason=f"Error in {subsystem}: {type(error).__name__}",
                )

                # ─── DIAGNOSE ─────────────────────────────────
                healing_event = await self._diagnose_and_repair(
                    error=error,
                    subsystem=subsystem,
                    context=ctx,
                    attempt=attempt,
                    cycle_start=cycle_start,
                )

                if healing_event:
                    self._event_history.append(healing_event)

                # ─── COOLDOWN ─────────────────────────────────
                if attempt < self.config.max_healing_attempts - 1:
                    self._phase = HealingPhase.COOLDOWN
                    await asyncio.sleep(self.config.cooldown_after_repair_s)

        # All attempts exhausted
        self._phase = HealingPhase.IDLE
        logger.error(
            "[AUTOCURATIVE] ❌ All %d healing attempts exhausted for '%s'",
            self.config.max_healing_attempts,
            subsystem,
        )
        ENDOCRINE.pulse(
            HormoneType.ADRENALINE,
            self.config.adrenaline_on_critical,
            reason=f"Healing exhausted: {subsystem}",
        )

        if last_error:
            raise last_error
        raise RuntimeError(f"AutoCurative: healing exhausted for '{subsystem}'")

    # ─── Core: Handle Error ──────────────────────────────────────

    async def handle_error(
        self,
        error: Exception,
        subsystem: str,
        context: dict[str, Any] | None = None,
    ) -> HealingEvent | None:
        """Handle a single error through the diagnosis → repair pipeline.

        Can be called directly when an error is caught elsewhere in the system.
        """
        ctx = context or {}
        cycle_start = time.perf_counter_ns()
        self._total_errors += 1

        breaker = self._get_or_create_breaker(subsystem)
        breaker._on_failure()

        event = await self._diagnose_and_repair(
            error=error,
            subsystem=subsystem,
            context=ctx,
            attempt=0,
            cycle_start=cycle_start,
        )

        if event:
            self._event_history.append(event)

        return event

    async def _diagnose_and_repair(
        self,
        error: Exception,
        subsystem: str,
        context: dict[str, Any],
        attempt: int,
        cycle_start: int,
    ) -> HealingEvent | None:
        """Internal: diagnose error and apply repair strategy."""

        # ─── DIAGNOSE ─────────────────────────────────────────
        self._phase = HealingPhase.DIAGNOSING
        error_sig = f"{type(error).__name__}: {str(error)[:500]}"

        diagnosis: dict[str, Any]
        if self._rust_engine is not None:
            # Fast-path: Rust diagnosis
            diagnosis = dict(self._rust_engine.diagnose(error_sig, subsystem))
        else:
            # Fallback: Python diagnosis
            diagnosis = self._python_diagnose(error_sig, subsystem)

        anomaly_class = diagnosis.get("anomaly_class", "UnclassifiedError")
        severity = diagnosis.get("severity", 0.5)
        strategy_name = diagnosis.get("repair_strategy", "LOG_AND_ESCALATE")
        repair_params = diagnosis.get("repair_parameters", {})
        diagnosis_time_ns = diagnosis.get("diagnosis_time_ns", 0)
        is_recurring = diagnosis.get("is_recurring", False)

        logger.warning(
            "[AUTOCURATIVE] 🔍 Diagnosis [%d/%d]: %s → %s (severity=%.2f, recurring=%s)",
            attempt + 1,
            self.config.max_healing_attempts,
            anomaly_class,
            strategy_name,
            severity,
            is_recurring,
        )

        # ─── REPAIR ───────────────────────────────────────────
        self._phase = HealingPhase.REPAIRING
        repair_result: RepairResult | None = None

        async with self._repair_semaphore:
            self._total_repairs += 1
            context["error_signature"] = error_sig
            context["anomaly_class"] = anomaly_class

            repair_result = await self._registry.execute(
                strategy_name=strategy_name,
                target=subsystem,
                parameters=repair_params,
                context=context,
            )

            if repair_result.succeeded:
                self._successful_repairs += 1
                if self._rust_engine is not None:
                    self._rust_engine.record_repair_outcome(True)
                logger.info(
                    "[AUTOCURATIVE] 🔧 Repair SUCCESS: %s → %s (%.2fms)",
                    strategy_name,
                    repair_result.message[:100],
                    repair_result.latency_ms,
                )
            else:
                if self._rust_engine is not None:
                    self._rust_engine.record_repair_outcome(False)
                logger.warning(
                    "[AUTOCURATIVE] ⚠️ Repair FAILED: %s → %s",
                    strategy_name,
                    repair_result.message[:100],
                )

        # ─── Build Event ──────────────────────────────────────
        total_cycle_ms = (time.perf_counter_ns() - cycle_start) / 1e6

        event = HealingEvent(
            timestamp_ns=time.time_ns(),
            phase=self._phase,
            error_signature=error_sig,
            anomaly_class=anomaly_class,
            subsystem=subsystem,
            severity=severity,
            repair_strategy=strategy_name,
            repair_result=repair_result,
            diagnosis_time_ns=diagnosis_time_ns,
            total_cycle_ms=total_cycle_ms,
            iteration=attempt,
        )

        return event

    def _python_diagnose(self, error_signature: str, subsystem: str) -> dict[str, Any]:
        """Pure-Python fallback diagnosis when Rust engine is unavailable."""
        lower = error_signature.lower()
        patterns = [
            ("timeout", "TimeoutCascade", 0.8, "INJECT_TIMEOUT_GUARD"),
            ("memory", "MemoryLeak", 0.9, "FORCE_GC_AND_REDUCE_BATCH"),
            ("connection", "ConnectionExhaustion", 0.85, "RESET_POOL_AND_RETRY"),
            ("rate", "RateLimitBreach", 0.5, "EXPONENTIAL_BACKOFF"),
            ("assert", "InvariantViolation", 1.0, "SNAPSHOT_AND_ROLLBACK"),
            ("serial", "SerializationCorruption", 0.7, "RESERIALIZE_WITH_VALIDATION"),
            ("circuit", "CircuitBreakerTripped", 0.95, "PROBE_AND_RESET_BREAKER"),
            ("heartbeat", "HeartbeatLost", 0.75, "RESTART_HEARTBEAT_EMITTER"),
            ("entropy", "EntropySpike", 0.6, "TRIGGER_CONSOLIDATION"),
        ]

        for keyword, aclass, severity, strategy in patterns:
            if keyword in lower:
                return {
                    "anomaly_class": aclass,
                    "severity": severity,
                    "repair_strategy": strategy,
                    "repair_parameters": {},
                    "diagnosis_time_ns": 0,
                    "is_recurring": False,
                }

        return {
            "anomaly_class": "UnclassifiedError",
            "severity": 0.3,
            "repair_strategy": "LOG_AND_ESCALATE",
            "repair_parameters": {},
            "diagnosis_time_ns": 0,
            "is_recurring": False,
        }

    # ─── Daemon Mode ──────────────────────────────────────────────

    async def start_daemon(
        self,
        engine: Any = None,
        project: str = "autocurative",
    ) -> None:
        """Start the self-healing daemon loop.

        Continuously monitors system health and triggers repairs
        when anomalies are detected. Integrates with the CORTEX engine's
        existing health infrastructure.
        """
        if self._is_running:
            logger.warning("[AUTOCURATIVE] Daemon already running")
            return

        self._is_running = True
        self._start_time = time.monotonic()
        logger.info(
            "[AUTOCURATIVE] 🚀 Level 5 Self-Healing Daemon started (interval=%.1fs)",
            self.config.monitor_interval_s,
        )

        while self._is_running:
            try:
                self._phase = HealingPhase.MONITORING

                # Health probe
                await self._probe_system_health(engine)
                cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)

                # Thresholds
                if cortisol > self.config.cortisol_alarm_threshold:
                    logger.warning(
                        "[AUTOCURATIVE] ⚠️ Cortisol alarm: %.3f > %.3f",
                        cortisol,
                        self.config.cortisol_alarm_threshold,
                    )
                    ENDOCRINE.pulse(
                        HormoneType.ADRENALINE,
                        0.05,
                        reason="Cortisol alarm threshold exceeded",
                    )

                # Check circuit breakers
                for name, breaker in self._breakers.items():
                    if breaker.state == CircuitState.OPEN:
                        logger.warning(
                            "[AUTOCURATIVE] Circuit '%s' is OPEN (trips=%d)",
                            name,
                            breaker.total_trips,
                        )

                self._phase = HealingPhase.IDLE

            except Exception as e:
                logger.error("[AUTOCURATIVE] Daemon probe error: %s", e)

            await asyncio.sleep(self.config.monitor_interval_s)

    async def _probe_system_health(self, engine: Any) -> dict[str, Any]:
        """Probe the CORTEX engine's health subsystems."""
        health: dict[str, Any] = {"status": "healthy", "timestamp": time.time()}

        if engine is not None:
            try:
                if hasattr(engine, "health_check"):
                    h = await asyncio.wait_for(engine.health_check(), timeout=5.0)
                    health.update(h if isinstance(h, dict) else {"engine_status": str(h)})
            except Exception as e:
                health["status"] = "degraded"
                health["error"] = str(e)

        return health

    def stop_daemon(self) -> None:
        """Stop the self-healing daemon."""
        self._is_running = False
        self._phase = HealingPhase.IDLE
        if self._daemon_task and not self._daemon_task.done():
            self._daemon_task.cancel()
        logger.info("[AUTOCURATIVE] Daemon stopped")

    # ─── Introspection ────────────────────────────────────────────

    @property
    def phase(self) -> HealingPhase:
        """Current phase of the self-healing loop."""
        return self._phase

    @property
    def health(self) -> AgentHealth:
        """Get the current health state of the agent."""
        uptime = time.monotonic() - self._start_time
        cortisol = ENDOCRINE.get_level(HormoneType.CORTISOL)

        # Health score
        if self._total_repairs > 0:
            repair_rate = self._successful_repairs / self._total_repairs
        else:
            repair_rate = 1.0

        recent_errors = sum(1 for e in self._event_history if e.severity > 0.7)
        health_score = max(0, min(100, 100 - recent_errors * 10)) * repair_rate

        # Status
        if health_score < self.config.health_score_critical:
            status = "critical"
        elif cortisol > self.config.cortisol_alarm_threshold:
            status = "degraded"
        elif self._phase == HealingPhase.REPAIRING:
            status = "healing"
        else:
            status = "healthy"

        return AgentHealth(
            status=status,
            uptime_s=uptime,
            total_errors_detected=self._total_errors,
            total_repairs_attempted=self._total_repairs,
            total_repairs_succeeded=self._successful_repairs,
            active_circuit_breakers={
                name: breaker.state.name for name, breaker in self._breakers.items()
            },
            cortisol_level=cortisol,
            health_score=health_score,
            recent_events=[e.to_dict() for e in list(self._event_history)[-10:]],
        )

    def get_healing_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent healing events."""
        events = list(self._event_history)
        return [e.to_dict() for e in events[-limit:]]

    def get_rust_metrics(self) -> dict[str, Any] | None:
        """Get metrics from the Rust fast-path engine."""
        if self._rust_engine is None:
            return None
        return dict(self._rust_engine.get_metrics())

    def reset_breaker(self, subsystem: str) -> bool:
        """Manually reset a circuit breaker."""
        breaker = self._breakers.get(subsystem)
        if breaker is not None:
            breaker.reset()
            return True
        return False

    def reset_all_breakers(self) -> int:
        """Reset all circuit breakers. Returns count reset."""
        count = 0
        for breaker in self._breakers.values():
            breaker.reset()
            count += 1
        return count
