"""CORTEX — Orchestrator Resilience Agent (Ω₅ Antifragile).

Addresses single points of failure (SPOFs), retries, and recovery semantics
in the CapatazOrchestrator / SwarmManager execution path.

This module is intentionally decoupled from OuroborosLifeline (feature layer)
and operates purely on execution-path durability.

Axiom Ω₅: Failures trigger degraded mode, not system death.
Write-Path Contract: any task execution that bypasses this layer is a SPOF.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TypeVar

__all__ = [
    "RetryPolicy",
    "RecoveryState",
    "SpofReport",
    "TaskFailureRecord",
    "OrchestratorResilience",
    "NON_RETRIABLE",
]

logger = logging.getLogger("cortex.extensions.swarm.resilience")

T = TypeVar("T")

# ── Sentinel set of exceptions that must never be retried ─────────────────────
# Elder rejections and deliberate business-logic halts are non-retriable.
NON_RETRIABLE: tuple[type[BaseException], ...] = (
    SystemExit,
    KeyboardInterrupt,
    MemoryError,
)


# ── RetryPolicy ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetryPolicy:
    """Configurable retry policy for orchestrator task execution.

    Implements truncated exponential back-off with optional full-jitter to
    spread thundering-herd pressure across concurrent agents.

    Attributes:
        max_attempts: Total number of attempts (1 = no retry).
        base_delay:   Initial back-off seconds (before jitter).
        max_delay:    Upper bound on any single wait (seconds).
        backoff_factor: Multiplier per successive failure (≥ 1.0).
        jitter:       When True, randomises delay in [0, computed_delay].
        non_retriable: Exception types that abort immediately without retry.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True
    non_retriable: tuple[type[BaseException], ...] = NON_RETRIABLE

    def delay_for(self, attempt: int) -> float:
        """Compute sleep duration (seconds) before the *next* attempt.

        Args:
            attempt: Zero-based attempt index of the attempt that just failed.

        Returns:
            Seconds to sleep; 0.0 when there are no more attempts.
        """
        if attempt + 1 >= self.max_attempts:
            return 0.0
        raw = min(self.base_delay * (self.backoff_factor**attempt), self.max_delay)
        # PRNG sufficient for load-distribution jitter; this is not a security-sensitive path.
        return random.uniform(0.0, raw) if self.jitter else raw  # noqa: S311

    def is_retriable(self, exc: BaseException) -> bool:
        """Return True iff *exc* is safe to retry under this policy."""
        return not isinstance(exc, self.non_retriable)


# ── RecoveryState ─────────────────────────────────────────────────────────────


class RecoveryState(Enum):
    """Lifecycle state of a resilience-managed component.

    NOMINAL    — operating within expected parameters.
    DEGRADED   — experiencing failures; retries in progress.
    RECOVERING — emitted HEALING signal; awaiting stabilisation.
    FAILED     — all retry budgets exhausted; manual intervention required.
    """

    NOMINAL = auto()
    DEGRADED = auto()
    RECOVERING = auto()
    FAILED = auto()


# ── SpofReport ────────────────────────────────────────────────────────────────


@dataclass
class SpofReport:
    """Snapshot of SPOF risk for a single orchestrator component.

    A component is classified as a SPOF when it has **no fallback** AND
    **no retry policy** — meaning a single transient failure terminates
    the entire execution path without any recovery opportunity.

    Attributes:
        component:     Human-readable component name (e.g. "capataz:run_task").
        has_fallback:  True iff an alternative code path exists on failure.
        retry_policy:  Attached RetryPolicy, or None if unguarded.
        is_spof:       Computed True when fallback=False and policy=None.
        risk_score:    Numeric risk (0.0–1.0): 1.0 = confirmed SPOF.
        recommendation: One-line mitigation guidance.
    """

    component: str
    has_fallback: bool
    retry_policy: RetryPolicy | None

    @property
    def is_spof(self) -> bool:
        return not self.has_fallback and self.retry_policy is None

    @property
    def risk_score(self) -> float:
        score = 0.0
        if not self.has_fallback:
            score += 0.5
        if self.retry_policy is None:
            score += 0.5
        elif self.retry_policy.max_attempts < 2:
            score += 0.25
        return min(score, 1.0)

    @property
    def recommendation(self) -> str:
        if self.is_spof:
            return (
                f"[CRITICAL] {self.component} is a SPOF — attach a RetryPolicy "
                "and register a fallback handler."
            )
        if not self.has_fallback:
            return f"[HIGH] {self.component} has no fallback — add an alternative execution path."
        if self.retry_policy is None:
            return f"[MEDIUM] {self.component} has a fallback but no retry policy."
        if self.retry_policy.max_attempts < 2:
            return (
                f"[LOW] {self.component} retry policy has max_attempts="
                f"{self.retry_policy.max_attempts} — consider increasing."
            )
        return f"[OK] {self.component} is resilient."


# ── TaskFailureRecord ─────────────────────────────────────────────────────────


@dataclass
class TaskFailureRecord:
    """Persists failure history for a named task across executions.

    Attributes:
        task_name:       Stable identifier for the task / agent combination.
        failure_count:   Total consecutive failures since last NOMINAL state.
        last_failure_at: Monotonic timestamp of the most recent failure.
        recovery_state:  Current lifecycle state.
        last_error:      String representation of the most recent exception.
    """

    task_name: str
    failure_count: int = 0
    last_failure_at: float = field(default_factory=time.monotonic)
    recovery_state: RecoveryState = RecoveryState.NOMINAL
    last_error: str = ""

    def record_failure(self, exc: BaseException) -> None:
        self.failure_count += 1
        self.last_failure_at = time.monotonic()
        self.last_error = str(exc)
        if self.recovery_state == RecoveryState.NOMINAL:
            self.recovery_state = RecoveryState.DEGRADED

    def record_success(self) -> None:
        if self.recovery_state != RecoveryState.NOMINAL:
            logger.info(
                "🟢 [resilience] %s recovered after %d failure(s)",
                self.task_name,
                self.failure_count,
            )
        self.failure_count = 0
        self.last_error = ""
        self.recovery_state = RecoveryState.NOMINAL

    def mark_recovering(self) -> None:
        self.recovery_state = RecoveryState.RECOVERING

    def mark_failed(self) -> None:
        self.recovery_state = RecoveryState.FAILED


# ── OrchestratorResilience ────────────────────────────────────────────────────


class OrchestratorResilience:
    """Resilience layer for CapatazOrchestrator task execution.

    Provides:
    - Retry-with-backoff around any async task coroutine.
    - SPOF inventory: reports which components lack retry or fallback.
    - Recovery-state tracking: aggregates per-task failure counters.
    - HEALING signal emission when a task exhausts its retry budget.

    Usage::

        resilience = OrchestratorResilience(signal_bus=bus)

        result = await resilience.execute_with_retry(
            my_coro_func,
            arg1,
            arg2,
            task_name="my_agent:my_task",
            policy=RetryPolicy(max_attempts=3),
        )

    The resilience instance is stateful: it accumulates ``TaskFailureRecord``
    objects so that recurring SPOF patterns surface in ``spof_summary()``.
    """

    def __init__(
        self,
        signal_bus: Any = None,
        default_policy: RetryPolicy | None = None,
    ) -> None:
        self._bus = signal_bus
        self._default_policy = default_policy or RetryPolicy()
        self._records: dict[str, TaskFailureRecord] = {}
        self._spof_registry: list[SpofReport] = []

    # ── Public API ─────────────────────────────────────────────────────

    async def execute_with_retry(
        self,
        coro_func: Callable[..., Awaitable[T]],
        *args: Any,
        task_name: str = "unknown",
        policy: RetryPolicy | None = None,
        **kwargs: Any,
    ) -> T:
        """Execute *coro_func* under retry semantics.

        On each failure the policy computes a back-off delay and re-invokes
        the coroutine until either the call succeeds or ``max_attempts`` is
        exhausted.  Non-retriable exceptions propagate immediately.

        Args:
            coro_func:  Async callable to execute.
            *args:      Positional arguments forwarded to *coro_func*.
            task_name:  Stable identifier used for failure tracking.
            policy:     Override policy; falls back to ``default_policy``.
            **kwargs:   Keyword arguments forwarded to *coro_func*.

        Returns:
            The return value of *coro_func* on success.

        Raises:
            The last exception raised by *coro_func* when all attempts fail.
        """
        active_policy = policy or self._default_policy
        record = self._get_or_create_record(task_name)

        # Invariant: max_attempts >= 1, so the loop always runs at least once and
        # last_exc is always assigned before being raised.  The initialiser is
        # purely defensive and should never surface to a caller.
        last_exc: BaseException = RuntimeError("No attempts made (max_attempts must be >= 1)")
        for attempt in range(active_policy.max_attempts):
            try:
                result = await coro_func(*args, **kwargs)
                record.record_success()
                return result
            except Exception as exc:
                if not active_policy.is_retriable(exc):
                    logger.error(
                        "🛑 [resilience] %s attempt %d/%d — non-retriable: %s",
                        task_name,
                        attempt + 1,
                        active_policy.max_attempts,
                        exc,
                    )
                    record.record_failure(exc)
                    raise

                last_exc = exc
                record.record_failure(exc)

                delay = active_policy.delay_for(attempt)
                remaining = active_policy.max_attempts - attempt - 1

                if remaining > 0:
                    logger.warning(
                        "⚡ [resilience] %s attempt %d/%d failed (%s). "
                        "Retrying in %.2fs (%d left).",
                        task_name,
                        attempt + 1,
                        active_policy.max_attempts,
                        exc,
                        delay,
                        remaining,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "💀 [resilience] %s exhausted %d attempt(s). Last error: %s",
                        task_name,
                        active_policy.max_attempts,
                        exc,
                    )
                    record.mark_failed()
                    await self._emit_healing_signal(task_name, record)

        raise last_exc

    def register_spof(
        self,
        component: str,
        *,
        has_fallback: bool = False,
        retry_policy: RetryPolicy | None = None,
    ) -> SpofReport:
        """Register a component in the SPOF inventory and return its report.

        Call this once per component at startup so that ``spof_summary()``
        reflects the full execution surface.

        Args:
            component:    Human-readable name of the component.
            has_fallback: Whether a secondary execution path exists.
            retry_policy: The RetryPolicy attached to this component, if any.

        Returns:
            A ``SpofReport`` for the component.
        """
        report = SpofReport(
            component=component,
            has_fallback=has_fallback,
            retry_policy=retry_policy,
        )
        self._spof_registry.append(report)
        if report.is_spof:
            log_level = logging.CRITICAL
            level_label = "CRITICAL"
        elif report.risk_score >= 0.5:
            log_level = logging.WARNING
            level_label = "HIGH"
        else:
            log_level = logging.DEBUG
            level_label = "OK"
        logger.log(
            log_level,
            "🔍 [resilience] SPOF scan — %s (risk=%.2f) [%s]",
            component,
            report.risk_score,
            level_label,
        )
        return report

    def spof_summary(self) -> list[SpofReport]:
        """Return all registered SPOF reports sorted by descending risk."""
        return sorted(self._spof_registry, key=lambda r: r.risk_score, reverse=True)

    def task_health(self, task_name: str) -> TaskFailureRecord | None:
        """Return the failure record for *task_name*, or None if never run."""
        return self._records.get(task_name)

    def all_task_health(self) -> dict[str, TaskFailureRecord]:
        """Snapshot of all accumulated task failure records."""
        return dict(self._records)

    def reset_task(self, task_name: str) -> None:
        """Manually reset a task to NOMINAL state (e.g. after operator intervention)."""
        if task_name in self._records:
            self._records[task_name].record_success()
            logger.info("🔄 [resilience] Task %s manually reset to NOMINAL.", task_name)

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_or_create_record(self, task_name: str) -> TaskFailureRecord:
        if task_name not in self._records:
            self._records[task_name] = TaskFailureRecord(task_name=task_name)
        return self._records[task_name]

    async def _emit_healing_signal(self, task_name: str, record: TaskFailureRecord) -> None:
        """Emit a HEALING intent signal so the swarm bus can react.

        Transitions the record to RECOVERING **only** when the signal is
        successfully emitted.  If there is no bus or emission fails, the
        record remains in FAILED state so that callers can distinguish between
        "healing requested" (RECOVERING) and "budget exhausted, no help sent"
        (FAILED).
        """
        if self._bus is None:
            return
        try:
            payload = {
                "task_name": task_name,
                "failure_count": record.failure_count,
                "last_error": record.last_error,
                "recovery_state": record.recovery_state.name,
            }
            await self._bus.emit(
                event_type="orchestrator:healing",
                payload=payload,
                source="OrchestratorResilience",
                project="CORTEX_SWARM",
            )
            record.mark_recovering()
            logger.info(
                "💊 [resilience] HEALING signal emitted for task %s after %d failures.",
                task_name,
                record.failure_count,
            )
        except Exception as bus_exc:  # noqa: BLE001 — signal emission must never crash the caller
            logger.debug(
                "[resilience] HEALING signal emission failed for %s: %s",
                task_name,
                bus_exc,
            )
