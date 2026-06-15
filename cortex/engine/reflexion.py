# [C5-REAL] Exergy-Maximized
"""Reflexion Engine - Self-Healing Dispatch Loop (Level 5).

Bridges the ISA builder's code-as-data primitives (reflect/rewrite) with a
structured self-improvement loop. When a dispatch tree execution fails:

1. REFLECT - Inspect the failed tree via ISA `reflect()`
2. DIAGNOSE - Generate structured analysis of the failure
3. REWRITE - Modify the tree via ISA `rewrite()` with corrections
4. RETRY - Re-execute with accumulated reflection context

Reflections are persisted for cross-session learning.

Architecture:
    ISA Builder (code-as-data) ←→ Reflexion Engine (loop) ←→ Guard Pipeline (safety)

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.isa.builder import (
    AgentOp,
    dispatch_targets,
    node_count,
    to_json,
)

__all__ = [
    "Reflection",
    "ReflexionConfig",
    "ReflexionEngine",
    "ReflexionOutcome",
]

logger = logging.getLogger("cortex.engine.reflexion")


# ─── Types ────────────────────────────────────────────────────────


class ReflexionVerdict(str, Enum):
    """Outcome of a single reflexion cycle."""

    SUCCESS = "success"
    RETRY = "retry"
    EXHAUSTED = "exhausted"
    ABORTED = "aborted"


@dataclass
class Reflection:
    """Structured reflection from a failed execution attempt.

    Each reflection captures not just WHAT failed, but WHY the agent
    thinks it failed and WHAT it would change. This is the core
    Nelson-Narens monitor signal (bottom-up from object-level to meta-level).
    """

    iteration: int
    timestamp_ns: int
    error_type: str
    error_message: str
    tree_snapshot: str  # JSON of the dispatch tree at failure
    tree_node_count: int
    tree_targets: list[str]
    diagnosis: str  # structured analysis of root cause
    proposed_fix: str  # what the rewrite should change
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "timestamp_ns": self.timestamp_ns,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "tree_node_count": self.tree_node_count,
            "tree_targets": self.tree_targets,
            "diagnosis": self.diagnosis,
            "proposed_fix": self.proposed_fix,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ReflexionOutcome:
    """Final result of the reflexion loop."""

    verdict: ReflexionVerdict
    result: Any = None
    iterations_used: int = 0
    reflections: list[Reflection] = field(default_factory=list)
    total_latency_ms: float = 0.0
    final_tree: AgentOp | None = None

    @property
    def succeeded(self) -> bool:
        return self.verdict == ReflexionVerdict.SUCCESS


@dataclass
class ReflexionConfig:
    """Guardrails for the reflexion loop."""

    max_iterations: int = 3
    timeout_ms: float = 30_000.0  # 30s total budget
    enable_tree_rewrite: bool = True
    persist_reflections: bool = True
    backoff_factor: float = 1.5  # exponential backoff between retries


# ─── Diagnosis & Rewriting Helpers ────────────────────────────────

from cortex.engine._reflexion_helpers import DiagnosisStrategy, TreeRewriter

# ─── Reflexion Engine ─────────────────────────────────────────────


class ReflexionEngine:
    """Self-Healing Dispatch Loop.

    Wraps task execution with automatic error capture, structured
    reflection, tree rewriting, and retry. Each iteration accumulates
    context that improves subsequent attempts.

    Usage:
        engine = ReflexionEngine()
        outcome = await engine.execute_with_reflexion(
            tree=my_dispatch_tree,
            executor=my_executor_fn,
        )
        if outcome.succeeded:
            logger.info(f"Solved in {outcome.iterations_used} iterations")
        else:
            logger.info(f"Failed after {outcome.iterations_used} attempts")
            for r in outcome.reflections:
                logger.info(f"  [{r.iteration}] {r.diagnosis}")
    """

    def __init__(self, config: ReflexionConfig | None = None) -> None:
        self.config = config or ReflexionConfig()
        self._reflection_memory: list[Reflection] = []
        self._session_stats = {
            "total_executions": 0,
            "total_reflections": 0,
            "success_rate": 1.0,
        }

    @property
    def reflection_memory(self) -> list[Reflection]:
        """Accumulated reflections from all executions (cross-task learning)."""
        return self._reflection_memory

    async def execute_with_reflexion(
        self,
        tree: AgentOp,
        executor: Callable[[AgentOp], Awaitable[Any]],
        *,
        task_context: str = "",
        on_reflection: Callable[[Reflection], Awaitable[None]] | None = None,
    ) -> ReflexionOutcome:
        """Execute a dispatch tree with automatic reflexion on failure.

        Args:
            tree: The ISA dispatch tree (code-as-data).
            executor: Async function that executes the tree and returns result.
            task_context: Human-readable description of the task (for diagnosis).
            on_reflection: Optional callback invoked after each reflection
                          (e.g., to persist to ledger or emit telemetry).

        Returns:
            ReflexionOutcome with verdict, result, and accumulated reflections.
        """
        self._session_stats["total_executions"] += 1
        reflections: list[Reflection] = []
        current_tree = tree
        loop_start = time.perf_counter_ns()
        backoff_ms = 100.0  # initial backoff

        for iteration in range(self.config.max_iterations):
            # ─── Budget check ─────────────────────────────────
            elapsed_ms = (time.perf_counter_ns() - loop_start) / 1e6
            if elapsed_ms > self.config.timeout_ms:
                logger.warning(
                    "[REFLEXION] Timeout budget exhausted (%.1fms / %.1fms) at iteration %d",
                    elapsed_ms,
                    self.config.timeout_ms,
                    iteration,
                )
                return ReflexionOutcome(
                    verdict=ReflexionVerdict.EXHAUSTED,
                    iterations_used=iteration,
                    reflections=reflections,
                    total_latency_ms=elapsed_ms,
                    final_tree=current_tree,
                )

            # ─── Execute ──────────────────────────────────────
            exec_start = time.perf_counter_ns()
            try:
                result = await executor(current_tree)

                # SUCCESS
                exec_ms = (time.perf_counter_ns() - exec_start) / 1e6
                total_ms = (time.perf_counter_ns() - loop_start) / 1e6

                if iteration > 0:
                    logger.info(
                        "[REFLEXION] ✅ Solved after %d reflexion(s) (%.1fms total)",
                        iteration,
                        total_ms,
                    )

                self._update_success_rate(True)
                self._emit_endocrine_reward(iteration)

                return ReflexionOutcome(
                    verdict=ReflexionVerdict.SUCCESS,
                    result=result,
                    iterations_used=iteration + 1,
                    reflections=reflections,
                    total_latency_ms=total_ms,
                    final_tree=current_tree,
                )

            except Exception as error:
                exec_ms = (time.perf_counter_ns() - exec_start) / 1e6

                # ─── REFLECT ──────────────────────────────────
                diagnosis, proposed_fix = DiagnosisStrategy.diagnose(error, current_tree)

                reflection = Reflection(
                    iteration=iteration,
                    timestamp_ns=time.time_ns(),
                    error_type=type(error).__name__,
                    error_message=str(error)[:500],
                    tree_snapshot=to_json(current_tree),
                    tree_node_count=node_count(current_tree),
                    tree_targets=dispatch_targets(current_tree),
                    diagnosis=diagnosis,
                    proposed_fix=proposed_fix,
                    latency_ms=exec_ms,
                )
                reflections.append(reflection)
                self._reflection_memory.append(reflection)
                self._session_stats["total_reflections"] += 1

                logger.warning(
                    "[REFLEXION] Iteration %d/%d failed: %s - %s",
                    iteration + 1,
                    self.config.max_iterations,
                    type(error).__name__,
                    diagnosis[:120],
                )

                # ─── Callback (persist / telemetry) ───────────
                if on_reflection is not None:
                    try:
                        await on_reflection(reflection)
                    except Exception as cb_err:
                        logger.debug("[REFLEXION] on_reflection callback error: %s", cb_err)

                # ─── REWRITE ──────────────────────────────────
                if self.config.enable_tree_rewrite and iteration < self.config.max_iterations - 1:
                    current_tree = self._apply_rewrite(current_tree, error, reflection, iteration)

                # ─── Backoff ──────────────────────────────────
                import asyncio

                await asyncio.sleep(backoff_ms / 1000.0)
                backoff_ms *= self.config.backoff_factor

        # All iterations exhausted
        total_ms = (time.perf_counter_ns() - loop_start) / 1e6
        self._update_success_rate(False)

        logger.error(
            "[REFLEXION] ❌ Exhausted after %d iterations (%.1fms). Reflections: %s",
            self.config.max_iterations,
            total_ms,
            [r.diagnosis[:80] for r in reflections],
        )

        return ReflexionOutcome(
            verdict=ReflexionVerdict.EXHAUSTED,
            iterations_used=self.config.max_iterations,
            reflections=reflections,
            total_latency_ms=total_ms,
            final_tree=current_tree,
        )

    def _apply_rewrite(
        self,
        tree: AgentOp,
        error: Exception,
        reflection: Reflection,
        iteration: int,
    ) -> AgentOp:
        """Apply structural rewrite to the dispatch tree based on reflection.

        Strategy selection is deterministic and based on error classification:
        - Iteration 0: Add retry wrappers (transient error assumption)
        - Iteration 1: Remove the failing target (isolation)
        - Iteration 2+: Add timeout guards (resource protection)
        """
        if iteration == 0:
            # First failure: assume transient, add retries
            logger.info("[REFLEXION] Rewrite strategy: RETRY_WRAPPER")
            return TreeRewriter.apply_retry_wrapper(tree, max_retries=2)

        if iteration == 1:
            # Second failure: isolate the problematic target
            targets = dispatch_targets(tree)
            if targets:
                failing_target = targets[-1]  # heuristic: last target likely failed
                logger.info(
                    "[REFLEXION] Rewrite strategy: REMOVE_TARGET(%s)",
                    failing_target,
                )
                return TreeRewriter.remove_failed_target(tree, failing_target)

        # Third+ failure: add defensive guards
        logger.info("[REFLEXION] Rewrite strategy: TIMEOUT_GUARD")
        return TreeRewriter.add_timeout_guard(tree, timeout_ms=5000)

    def _update_success_rate(self, success: bool) -> None:
        """Exponential moving average of success rate (self-model calibration)."""
        alpha = 0.1
        current = 1.0 if success else 0.0
        self._session_stats["success_rate"] = (
            alpha * current + (1 - alpha) * self._session_stats["success_rate"]
        )

    def _emit_endocrine_reward(self, iterations_used: int) -> None:
        """Emit hormonal signals based on reflexion outcome."""
        try:
            from cortex.engine.endocrine import ENDOCRINE, HormoneType

            if iterations_used == 0:
                # First-try success: reward
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.02)
            elif iterations_used > 0:
                # Solved after reflection: moderate reward + cortisol recovery
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.01)
                ENDOCRINE.pulse(HormoneType.CORTISOL, -0.02)
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)

    # Endocrine system not available

    def get_session_stats(self) -> dict[str, Any]:
        """Return session-level metrics for the meta-level monitor."""
        return {
            **self._session_stats,
            "reflection_memory_size": len(self._reflection_memory),
            "failure_patterns": self._extract_failure_patterns(),
        }

    def _extract_failure_patterns(self) -> dict[str, int]:
        """Aggregate failure patterns from reflection memory (meta-learning)."""
        patterns: dict[str, int] = {}
        for r in self._reflection_memory:
            patterns[r.error_type] = patterns.get(r.error_type, 0) + 1
        return patterns

    def get_accumulated_context(self, max_reflections: int = 5) -> str:
        """Build accumulated reflection context for injection into prompts.

        Returns the most recent N reflections as structured text that can
        be prepended to LLM context for cross-task learning.
        """
        if not self._reflection_memory:
            return ""

        recent = self._reflection_memory[-max_reflections:]
        lines = ["LESSONS FROM PREVIOUS FAILURES:"]
        for r in recent:
            lines.append(f"  [{r.error_type}] {r.diagnosis[:120]} → Fix: {r.proposed_fix[:80]}")
        return "\n".join(lines)
