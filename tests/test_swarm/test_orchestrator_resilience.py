"""Tests for OrchestratorResilience — SPOFs, retries, recovery semantics.

Covers:
- RetryPolicy.delay_for / is_retriable
- OrchestratorResilience.execute_with_retry (success, transient, exhausted, non-retriable)
- SpofReport risk classification and recommendations
- TaskFailureRecord state transitions
- HEALING signal emission on exhausted budget
- register_spof / spof_summary sorting
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.swarm.resilience import (
    NON_RETRIABLE,
    OrchestratorResilience,
    RecoveryState,
    RetryPolicy,
    SpofReport,
    TaskFailureRecord,
)

# ── RetryPolicy ────────────────────────────────────────────────────────────────


class TestRetryPolicy:
    def test_delay_for_last_attempt_is_zero(self) -> None:
        policy = RetryPolicy(max_attempts=3, base_delay=1.0, jitter=False)
        # attempt index 2 is the last (0-based) for max_attempts=3
        assert policy.delay_for(2) == 0.0

    def test_delay_increases_exponentially(self) -> None:
        policy = RetryPolicy(
            max_attempts=5, base_delay=1.0, backoff_factor=2.0, max_delay=100.0, jitter=False
        )
        d0 = policy.delay_for(0)  # 1.0 * 2^0 = 1.0
        d1 = policy.delay_for(1)  # 1.0 * 2^1 = 2.0
        d2 = policy.delay_for(2)  # 1.0 * 2^2 = 4.0
        assert d0 == pytest.approx(1.0)
        assert d1 == pytest.approx(2.0)
        assert d2 == pytest.approx(4.0)

    def test_delay_capped_at_max_delay(self) -> None:
        policy = RetryPolicy(
            max_attempts=10, base_delay=1.0, backoff_factor=10.0, max_delay=5.0, jitter=False
        )
        # 1.0 * 10^3 = 1000 but capped at 5.0
        assert policy.delay_for(3) == pytest.approx(5.0)

    def test_jitter_stays_within_bounds(self) -> None:
        policy = RetryPolicy(max_attempts=5, base_delay=1.0, backoff_factor=2.0, jitter=True)
        for attempt in range(3):
            d = policy.delay_for(attempt)
            raw = min(1.0 * (2.0**attempt), 30.0)
            assert 0.0 <= d <= raw + 1e-9  # float tolerance

    def test_is_retriable_standard_exception(self) -> None:
        policy = RetryPolicy()
        assert policy.is_retriable(ValueError("transient")) is True

    def test_is_retriable_non_retriable_exceptions(self) -> None:
        policy = RetryPolicy()
        for exc_type in NON_RETRIABLE:
            assert policy.is_retriable(exc_type()) is False

    def test_custom_non_retriable_overrides(self) -> None:
        policy = RetryPolicy(non_retriable=(*NON_RETRIABLE, RuntimeError))
        assert policy.is_retriable(RuntimeError("elder rejection")) is False
        assert policy.is_retriable(ConnectionError("transient")) is True


# ── SpofReport ─────────────────────────────────────────────────────────────────


class TestSpofReport:
    def test_is_spof_no_fallback_no_policy(self) -> None:
        report = SpofReport("engine:store", has_fallback=False, retry_policy=None)
        assert report.is_spof is True
        assert report.risk_score == pytest.approx(1.0)

    def test_not_spof_with_fallback(self) -> None:
        report = SpofReport("engine:store", has_fallback=True, retry_policy=None)
        assert report.is_spof is False
        assert report.risk_score == pytest.approx(0.5)

    def test_not_spof_with_retry_policy(self) -> None:
        policy = RetryPolicy(max_attempts=3)
        report = SpofReport("engine:store", has_fallback=False, retry_policy=policy)
        assert report.is_spof is False
        assert report.risk_score == pytest.approx(0.5)

    def test_fully_resilient_zero_risk(self) -> None:
        policy = RetryPolicy(max_attempts=3)
        report = SpofReport("engine:store", has_fallback=True, retry_policy=policy)
        assert report.is_spof is False
        assert report.risk_score == pytest.approx(0.0)

    def test_recommendation_critical_for_spof(self) -> None:
        report = SpofReport("capataz:run_task", has_fallback=False, retry_policy=None)
        assert "CRITICAL" in report.recommendation
        assert "SPOF" in report.recommendation

    def test_recommendation_ok_for_resilient(self) -> None:
        report = SpofReport(
            "capataz:run_task", has_fallback=True, retry_policy=RetryPolicy(max_attempts=3)
        )
        assert report.recommendation.startswith("[OK]")


# ── TaskFailureRecord ──────────────────────────────────────────────────────────


class TestTaskFailureRecord:
    def test_initial_state_is_nominal(self) -> None:
        rec = TaskFailureRecord(task_name="my_task")
        assert rec.recovery_state == RecoveryState.NOMINAL
        assert rec.failure_count == 0

    def test_first_failure_transitions_to_degraded(self) -> None:
        rec = TaskFailureRecord(task_name="my_task")
        rec.record_failure(ValueError("boom"))
        assert rec.recovery_state == RecoveryState.DEGRADED
        assert rec.failure_count == 1
        assert "boom" in rec.last_error

    def test_success_resets_to_nominal(self) -> None:
        rec = TaskFailureRecord(task_name="my_task")
        rec.record_failure(ValueError("boom"))
        rec.record_success()
        assert rec.recovery_state == RecoveryState.NOMINAL
        assert rec.failure_count == 0
        assert rec.last_error == ""

    def test_mark_failed_transitions(self) -> None:
        rec = TaskFailureRecord(task_name="my_task")
        rec.record_failure(ValueError("x"))
        rec.mark_failed()
        assert rec.recovery_state == RecoveryState.FAILED

    def test_mark_recovering_transitions(self) -> None:
        rec = TaskFailureRecord(task_name="my_task")
        rec.record_failure(ValueError("x"))
        rec.mark_recovering()
        assert rec.recovery_state == RecoveryState.RECOVERING


# ── OrchestratorResilience.execute_with_retry ──────────────────────────────────


class TestExecuteWithRetry:
    async def test_immediate_success(self) -> None:
        resilience = OrchestratorResilience()
        call_count = 0

        async def ok_task() -> str:
            nonlocal call_count
            call_count += 1
            return "done"

        result = await resilience.execute_with_retry(ok_task, task_name="ok")
        assert result == "done"
        assert call_count == 1
        rec = resilience.task_health("ok")
        assert rec is not None
        assert rec.recovery_state == RecoveryState.NOMINAL

    async def test_transient_failure_retried_to_success(self) -> None:
        resilience = OrchestratorResilience(
            default_policy=RetryPolicy(max_attempts=3, base_delay=0.0, jitter=False)
        )
        call_count = 0

        async def flaky_task() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "recovered"

        result = await resilience.execute_with_retry(flaky_task, task_name="flaky")
        assert result == "recovered"
        assert call_count == 3
        assert resilience.task_health("flaky").recovery_state == RecoveryState.NOMINAL  # type: ignore[union-attr]

    async def test_exhausted_attempts_raises_last_exception(self) -> None:
        resilience = OrchestratorResilience(
            default_policy=RetryPolicy(max_attempts=2, base_delay=0.0, jitter=False)
        )

        async def always_fails() -> str:
            raise ValueError("persistent failure")

        with pytest.raises(ValueError, match="persistent failure"):
            await resilience.execute_with_retry(always_fails, task_name="broken")

        rec = resilience.task_health("broken")
        assert rec is not None
        assert rec.recovery_state == RecoveryState.FAILED

    async def test_non_retriable_exception_propagates_immediately(self) -> None:
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=0.0,
            jitter=False,
            non_retriable=(*NON_RETRIABLE, RuntimeError),
        )
        resilience = OrchestratorResilience(default_policy=policy)
        call_count = 0

        async def elder_rejection() -> str:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Elder rejection — no retry")

        with pytest.raises(RuntimeError, match="Elder rejection"):
            await resilience.execute_with_retry(
                elder_rejection, task_name="elder", policy=policy
            )

        # Must abort on first attempt, not retry
        assert call_count == 1

    async def test_healing_signal_emitted_on_exhaustion(self) -> None:
        mock_bus = MagicMock()
        mock_bus.emit = AsyncMock()

        resilience = OrchestratorResilience(
            signal_bus=mock_bus,
            default_policy=RetryPolicy(max_attempts=2, base_delay=0.0, jitter=False),
        )

        async def always_fails() -> None:
            raise ConnectionError("provider down")

        with pytest.raises(ConnectionError):
            await resilience.execute_with_retry(always_fails, task_name="dying_task")

        mock_bus.emit.assert_awaited_once()
        call_kwargs = mock_bus.emit.call_args.kwargs
        assert call_kwargs["event_type"] == "orchestrator:healing"
        assert call_kwargs["payload"]["task_name"] == "dying_task"

    async def test_healing_signal_not_emitted_on_success(self) -> None:
        mock_bus = MagicMock()
        mock_bus.emit = AsyncMock()

        resilience = OrchestratorResilience(signal_bus=mock_bus)

        async def ok_task() -> str:
            return "fine"

        await resilience.execute_with_retry(ok_task, task_name="ok_task")
        mock_bus.emit.assert_not_awaited()

    async def test_bus_failure_does_not_crash_caller(self) -> None:
        mock_bus = MagicMock()
        mock_bus.emit = AsyncMock(side_effect=RuntimeError("bus dead"))

        resilience = OrchestratorResilience(
            signal_bus=mock_bus,
            default_policy=RetryPolicy(max_attempts=1, base_delay=0.0),
        )

        async def fails() -> None:
            raise ConnectionError("net")

        # The HEALING signal emit failure must not propagate to the caller
        with pytest.raises(ConnectionError):
            await resilience.execute_with_retry(fails, task_name="net_task")

    async def test_per_call_policy_overrides_default(self) -> None:
        default_policy = RetryPolicy(max_attempts=5, base_delay=0.0, jitter=False)
        override_policy = RetryPolicy(max_attempts=1, base_delay=0.0, jitter=False)
        resilience = OrchestratorResilience(default_policy=default_policy)

        call_count = 0

        async def fails() -> None:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("net")

        with pytest.raises(ConnectionError):
            await resilience.execute_with_retry(fails, task_name="t", policy=override_policy)

        # override: max_attempts=1 → only 1 call despite default allowing 5
        assert call_count == 1


# ── register_spof / spof_summary ───────────────────────────────────────────────


class TestSpofRegistry:
    def test_register_spof_returns_report(self) -> None:
        r = OrchestratorResilience()
        report = r.register_spof("comp:a", has_fallback=False, retry_policy=None)
        assert isinstance(report, SpofReport)
        assert report.is_spof is True

    def test_spof_summary_sorted_by_risk_descending(self) -> None:
        r = OrchestratorResilience()
        r.register_spof("low_risk", has_fallback=True, retry_policy=RetryPolicy(max_attempts=3))
        r.register_spof("high_risk", has_fallback=False, retry_policy=None)
        r.register_spof("medium_risk", has_fallback=True, retry_policy=None)

        summary = r.spof_summary()
        assert summary[0].component == "high_risk"
        assert summary[0].risk_score == pytest.approx(1.0)
        assert summary[-1].component == "low_risk"

    def test_register_multiple_same_component_allowed(self) -> None:
        r = OrchestratorResilience()
        r.register_spof("dup", has_fallback=False)
        r.register_spof("dup", has_fallback=True)
        assert len(r.spof_summary()) == 2


# ── reset_task / all_task_health ───────────────────────────────────────────────


class TestTaskHealthManagement:
    async def test_reset_task_returns_to_nominal(self) -> None:
        r = OrchestratorResilience(
            default_policy=RetryPolicy(max_attempts=1, base_delay=0.0)
        )

        async def fails() -> None:
            raise ValueError("x")

        with pytest.raises(ValueError):
            await r.execute_with_retry(fails, task_name="t1")

        assert r.task_health("t1").recovery_state == RecoveryState.FAILED  # type: ignore[union-attr]
        r.reset_task("t1")
        assert r.task_health("t1").recovery_state == RecoveryState.NOMINAL  # type: ignore[union-attr]

    async def test_all_task_health_snapshot(self) -> None:
        r = OrchestratorResilience(
            default_policy=RetryPolicy(max_attempts=1, base_delay=0.0)
        )

        async def ok() -> str:
            return "x"

        async def bad() -> None:
            raise ConnectionError("net")

        await r.execute_with_retry(ok, task_name="good")
        with pytest.raises(ConnectionError):
            await r.execute_with_retry(bad, task_name="bad")

        health = r.all_task_health()
        assert "good" in health
        assert "bad" in health
        assert health["good"].recovery_state == RecoveryState.NOMINAL
        assert health["bad"].recovery_state == RecoveryState.FAILED
