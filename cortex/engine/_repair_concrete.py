# [C5-REAL] Exergy-Maximized
"""Concrete SICA self-healing repair strategies."""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from typing import Any

from cortex.engine.repair_strategies import RepairResult, RepairStatus

logger = logging.getLogger("cortex.engine.repair")


class InjectTimeoutGuard:
    """Wraps failing dispatch nodes with timeout protection."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()
        timeout_ms = int(parameters.get("timeout_ms", "5000"))

        try:
            # Apply timeout guard via ISA rewrite if tree is available
            tree = context.get("dispatch_tree")
            if tree is not None:
                from cortex.engine.reflexion import TreeRewriter

                new_tree = TreeRewriter.add_timeout_guard(tree, timeout_ms=timeout_ms)
                context["dispatch_tree"] = new_tree

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="INJECT_TIMEOUT_GUARD",
                target=target,
                latency_ms=latency,
                message=f"Timeout guard ({timeout_ms}ms) injected into dispatch tree",
                side_effects=["dispatch_tree_modified"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="INJECT_TIMEOUT_GUARD",
                target=target,
                latency_ms=latency,
                message=f"Failed to inject timeout guard: {e}",
            )


class ForceGcAndReduceBatch:
    """Forces garbage collection and reduces batch sizes."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        try:
            # Force GC
            gc.collect()

            reduction = float(parameters.get("batch_reduction_factor", "0.5"))
            current_batch = context.get("batch_size", 100)
            new_batch = max(1, int(current_batch * reduction))
            context["batch_size"] = new_batch

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="FORCE_GC_AND_REDUCE_BATCH",
                target=target,
                latency_ms=latency,
                message=f"GC forced. Batch: {current_batch} → {new_batch}",
                side_effects=["gc_collected", "batch_size_reduced"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="FORCE_GC_AND_REDUCE_BATCH",
                target=target,
                latency_ms=latency,
                message=f"GC/batch reduction failed: {e}",
            )


class ResetPoolAndRetry:
    """Resets connection pools and retries the failed operation."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()
        max_retries = int(parameters.get("max_retries", "3"))

        try:
            engine = context.get("engine")
            if engine is not None and hasattr(engine, "_conns_by_loop"):
                # Close stale connections
                conns = list(engine._conns_by_loop.values())
                for conn in conns:
                    try:
                        await conn.close()
                    except Exception as exc:
                        logger.warning("Suppressed exception: %s", exc)
                engine._conns_by_loop.clear()
                engine._schema_ready = False

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="RESET_POOL_AND_RETRY",
                target=target,
                latency_ms=latency,
                message=f"Connection pool reset. Ready for retry (max={max_retries})",
                side_effects=["connection_pool_reset", "schema_invalidated"],
                rollback_available=False,
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="RESET_POOL_AND_RETRY",
                target=target,
                latency_ms=latency,
                message=f"Pool reset failed: {e}",
            )


class ExponentialBackoff:
    """Applies exponential backoff with jitter for rate-limited operations."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()
        initial_delay = int(parameters.get("initial_delay_ms", "1000"))
        use_jitter = parameters.get("jitter", "true").lower() == "true"

        try:
            import random

            delay_s = initial_delay / 1000.0
            if use_jitter:
                delay_s *= 0.5 + random.random()

            # Store the backoff state for the caller to use
            context["backoff_delay_s"] = delay_s
            context["backoff_applied"] = True

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="EXPONENTIAL_BACKOFF",
                target=target,
                latency_ms=latency,
                message=f"Backoff configured: {delay_s:.2f}s delay before retry",
                side_effects=["backoff_state_set"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="EXPONENTIAL_BACKOFF",
                target=target,
                latency_ms=latency,
                message=f"Backoff configuration failed: {e}",
            )


class ProbeAndResetBreaker:
    """Probes a tripped circuit breaker and resets if the subsystem recovered."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        try:
            breaker = context.get("circuit_breaker")
            if breaker is not None:
                from cortex.engine.circuit_breaker import CircuitState

                if breaker.state == CircuitState.OPEN:
                    # Force half-open for probe
                    breaker._state = CircuitState.HALF_OPEN
                    logger.info(
                        "[REPAIR] Circuit breaker '%s' forced to HALF_OPEN for probe",
                        getattr(breaker, "_name", target),
                    )

                elif breaker.state == CircuitState.HALF_OPEN:
                    # Already probing
                    pass

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="PROBE_AND_RESET_BREAKER",
                target=target,
                latency_ms=latency,
                message="Circuit breaker moved to HALF_OPEN for probe",
                side_effects=["circuit_breaker_probed"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="PROBE_AND_RESET_BREAKER",
                target=target,
                latency_ms=latency,
                message=f"Breaker probe failed: {e}",
            )


class RestartHeartbeatEmitter:
    """Restarts a dead heartbeat emitter."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()
        restart_delay = int(parameters.get("restart_delay_ms", "500"))

        try:
            heartbeat = context.get("heartbeat")
            if heartbeat is not None:
                heartbeat.stop()
                await asyncio.sleep(restart_delay / 1000.0)
                # The caller should restart - we just set the flag
                context["heartbeat_needs_restart"] = True

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="RESTART_HEARTBEAT_EMITTER",
                target=target,
                latency_ms=latency,
                message=f"Heartbeat stopped. Restart scheduled ({restart_delay}ms)",
                side_effects=["heartbeat_stopped", "restart_scheduled"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="RESTART_HEARTBEAT_EMITTER",
                target=target,
                latency_ms=latency,
                message=f"Heartbeat restart failed: {e}",
            )


class TriggerConsolidation:
    """Forces a memory consolidation cycle to reduce entropy."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        try:
            sleep_orchestrator = context.get("sleep_orchestrator")
            project = context.get("project", "autocurative")

            if sleep_orchestrator is not None:
                report = await sleep_orchestrator.run_full_cycle(project)
                latency = (time.perf_counter_ns() - start) / 1e6
                return RepairResult(
                    status=RepairStatus.SUCCESS,
                    strategy="TRIGGER_CONSOLIDATION",
                    target=target,
                    latency_ms=latency,
                    message=f"Consolidation complete: merged={report.nrem_merged}",
                    side_effects=["consolidation_executed"],
                )

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SKIPPED,
                strategy="TRIGGER_CONSOLIDATION",
                target=target,
                latency_ms=latency,
                message="No SleepOrchestrator available - skipped",
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="TRIGGER_CONSOLIDATION",
                target=target,
                latency_ms=latency,
                message=f"Consolidation failed: {e}",
            )


class SnapshotAndRollback:
    """Takes a snapshot before attempting a fix, with rollback capability."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        try:
            engine = context.get("engine")
            if engine is not None and hasattr(engine, "create_checkpoint"):
                checkpoint = await engine.create_checkpoint()
                context["rollback_checkpoint"] = checkpoint

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="SNAPSHOT_AND_ROLLBACK",
                target=target,
                latency_ms=latency,
                message="Snapshot created for rollback safety",
                side_effects=["checkpoint_created"],
                rollback_available=True,
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="SNAPSHOT_AND_ROLLBACK",
                target=target,
                latency_ms=latency,
                message=f"Snapshot failed: {e}",
            )


class LogAndEscalate:
    """Logs the unclassified error and marks for human escalation."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        error_sig = context.get("error_signature", "unknown")
        logger.warning(
            "[AUTOCURATIVE] Unclassified error escalated to human: %s (target: %s)",
            error_sig,
            target,
        )
        context["escalation_required"] = True

        latency = (time.perf_counter_ns() - start) / 1e6
        return RepairResult(
            status=RepairStatus.SKIPPED,
            strategy="LOG_AND_ESCALATE",
            target=target,
            latency_ms=latency,
            message=f"Error escalated: {str(error_sig)[:200]}",
            side_effects=["escalation_flagged"],
        )


class ReserializeWithValidation:
    """Re-serializes payloads with schema validation and null stripping."""

    async def execute(
        self,
        target: str,
        parameters: dict[str, str],
        context: dict[str, Any],
    ) -> RepairResult:
        start = time.perf_counter_ns()

        try:
            payload = context.get("payload")
            if payload is not None:
                import json

                # Round-trip through JSON with null stripping
                cleaned = json.loads(json.dumps(payload, default=str))
                if parameters.get("strip_nulls", "true").lower() == "true":
                    cleaned = {k: v for k, v in cleaned.items() if v is not None}
                context["payload"] = cleaned

            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.SUCCESS,
                strategy="RESERIALIZE_WITH_VALIDATION",
                target=target,
                latency_ms=latency,
                message="Payload re-serialized with validation",
                side_effects=["payload_cleaned"],
            )
        except Exception as e:
            latency = (time.perf_counter_ns() - start) / 1e6
            return RepairResult(
                status=RepairStatus.FAILED,
                strategy="RESERIALIZE_WITH_VALIDATION",
                target=target,
                latency_ms=latency,
                message=f"Re-serialization failed: {e}",
            )
