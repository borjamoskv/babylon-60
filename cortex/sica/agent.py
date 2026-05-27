"""SICA Agent — The Integrated Self-Improving Cognitive Architecture.

Integrates the three SICA layers into a single agent that inherits
from CORTEX BaseAgent:

  ┌─────────────────────────────────────────┐
  │            META-LEVEL                    │
  │  Constitution + MetaLevel                │
  │  "Was my strategy correct?"              │
  │         MONITORS ↑   ↓ CONTROLS          │
  │  ┌──────────────────────────────────┐    │
  │  │         OBJECT-LEVEL             │    │
  │  │  SearchStrategy + ObjectLevel    │    │
  │  │  plan → tools → result           │    │
  │  └──────────────────────────────────┘    │
  └─────────────────────────────────────────┘

The SICAAgent lifecycle per task:
  1. Receive task (handle_message)
  2. Object-level begins execution trace
  3. Object-level executes steps guided by current strategy
  4. Object-level finalizes trace
  5. Meta-level MONITORS the trace → produces MetaJudgment
  6. Meta-level CONTROLS the strategy → applies mutations
  7. Constitutional evaluation gates the output
  8. Result emitted (or revised/aborted)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.state import AgentStatus
from cortex.agents.tools import ToolRegistry
from cortex.sica.constitution import Constitution, Severity
from cortex.sica.meta_level import MetaLevel, MetaJudgment, MetaAction
from cortex.sica.object_level import ObjectLevel, StepOutcome
from cortex.sica.strategy import SearchStrategy, default_genome

logger = logging.getLogger("cortex.sica.agent")


class SICAAgent(BaseAgent):
    """Self-Improving Cognitive Architecture Agent.

    A CORTEX agent that monitors its own reasoning process and
    evolves its search strategy across task executions.

    The agent distinguishes between:
      - Object-level failures: "the task failed" → retry/fix
      - Meta-level failures: "my thinking was wrong" → mutate strategy

    This implements Nelson-Narens (1990) metacognitive architecture
    with Anthropic Constitutional AI output gating.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        constitution: Constitution | None = None,
        strategy: SearchStrategy | None = None,
        max_retries_per_task: int = 3,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._strategy = strategy or SearchStrategy(default_genome())
        self._object_level = ObjectLevel(self._strategy)
        self._meta_level = MetaLevel(self._strategy, constitution)
        self._max_retries = max_retries_per_task
        self._task_counter = 0
        self._lifetime_stats = _LifetimeStats()

    @property
    def strategy(self) -> SearchStrategy:
        return self._strategy

    @property
    def meta_level(self) -> MetaLevel:
        return self._meta_level

    @property
    def object_level(self) -> ObjectLevel:
        return self._object_level

    # ── BaseAgent Implementation ─────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Process an incoming message through the SICA loop."""
        if message.kind == MessageKind.TASK_REQUEST:
            await self._execute_task(message)
        elif message.kind == MessageKind.HEARTBEAT:
            await self.emit_heartbeat()
        else:
            logger.debug("[%s] Ignoring message kind=%s", self.agent_id, message.kind)

    async def on_start(self) -> None:
        logger.info(
            "[%s] SICA Agent started (genome gen=%d, hash=%s)",
            self.agent_id,
            self._strategy.genome.generation,
            self._strategy.genome.genome_hash,
        )

    async def on_stop(self) -> None:
        logger.info(
            "[%s] SICA Agent stopped. Lifetime: %s",
            self.agent_id,
            self._lifetime_stats.summary(),
        )

    # ── Core SICA Loop ───────────────────────────────────────────

    async def _execute_task(self, message: AgentMessage) -> None:
        """Execute a task through the full SICA metacognitive loop.

        This is where Nelson-Narens comes alive:
          1. Object-level executes
          2. Meta-level monitors
          3. Meta-level controls (mutates strategy if needed)
          4. Constitution gates output
        """
        self._task_counter += 1
        task_id = message.payload.get("task_id", f"sica-{self._task_counter}")
        objective = message.payload.get("objective", "")
        task_input = message.payload.get("input", {})

        logger.info(
            "[%s] SICA task %s: %s",
            self.agent_id,
            task_id,
            objective[:100],
        )

        retry_count = 0
        last_judgment: MetaJudgment | None = None

        while retry_count <= self._max_retries:
            # ── Phase 1: Object-Level Execution ──────────────────
            trace = self._object_level.begin_task(task_id, objective)

            try:
                result = await self._run_object_level(task_input, objective)
                outcome = StepOutcome.SUCCESS
            except Exception as exc:  # noqa: BLE001
                self._object_level.record_step(
                    action="task_execution",
                    outcome=StepOutcome.FAILURE,
                    error=repr(exc),
                )
                result = {"error": repr(exc)}
                outcome = StepOutcome.FAILURE

            # Assess own confidence
            confidence = self._self_assess_confidence(outcome)
            trace = self._object_level.end_task(outcome, confidence=confidence)

            # ── Phase 2: Meta-Level MONITOR ──────────────────────
            judgment = self._meta_level.monitor(trace)
            last_judgment = judgment

            self._lifetime_stats.record_judgment(judgment)

            logger.info(
                "[%s] Meta-judgment: class=%s meta_failure=%s confidence=%.2f",
                self.agent_id,
                judgment.failure_class.value if judgment.failure_class else "none",
                judgment.is_meta_failure,
                judgment.confidence,
            )

            # ── Phase 3: Meta-Level CONTROL ──────────────────────
            if judgment.requires_strategy_mutation:
                mutations = self._meta_level.control(judgment)
                self._lifetime_stats.mutations += len(mutations)
                logger.info(
                    "[%s] Applied %d strategy mutations (gen=%d)",
                    self.agent_id,
                    len(mutations),
                    self._strategy.genome.generation,
                )

            # ── Phase 4: Constitutional Gate ─────────────────────
            if judgment.constitutional_verdict and judgment.constitutional_verdict.abort_needed:
                logger.error(
                    "[%s] CONSTITUTIONAL ABORT — cardinal violation on task %s",
                    self.agent_id,
                    task_id,
                )
                await self._emit_abort(message, task_id, judgment)
                return

            # ── Phase 5: Success or Retry Decision ───────────────
            if outcome == StepOutcome.SUCCESS:
                # Check constitutional revision requirement
                if (
                    judgment.constitutional_verdict
                    and judgment.constitutional_verdict.revision_needed
                ):
                    logger.warning(
                        "[%s] Output requires constitutional revision",
                        self.agent_id,
                    )
                    result = self._revise_output(result, judgment)

                await self._emit_result(message, task_id, result, judgment)
                return

            # Failure — should we retry?
            if judgment.is_meta_failure:
                # Meta-failure: strategy was mutated, retry with new genome
                retry_count += 1
                logger.info(
                    "[%s] Meta-failure detected. Retrying with mutated strategy "
                    "(attempt %d/%d, genome=%s)",
                    self.agent_id,
                    retry_count,
                    self._max_retries,
                    self._strategy.genome.genome_hash,
                )
                continue
            else:
                # Object-failure: simple retry without strategy change
                retry_count += 1
                if retry_count <= self._max_retries:
                    logger.info(
                        "[%s] Object-level failure. Simple retry (%d/%d)",
                        self.agent_id,
                        retry_count,
                        self._max_retries,
                    )
                    continue

        # Exhausted retries
        logger.error(
            "[%s] Task %s exhausted %d retries",
            self.agent_id,
            task_id,
            self._max_retries,
        )

        # Check if we should escalate
        if last_judgment and MetaAction.ESCALATE_TO_HUMAN in last_judgment.recommended_actions:
            await self._emit_escalation(message, task_id, last_judgment)
        else:
            await self._emit_failure(message, task_id, last_judgment)

    async def _run_object_level(
        self,
        task_input: dict[str, Any],
        objective: str,
    ) -> dict[str, Any]:
        """Execute the actual task using available tools.

        This is where subclasses plug in domain-specific logic.
        The base implementation provides a strategy-guided execution skeleton.
        """
        genome = self._strategy.genome

        # Step 1: Decomposition check
        difficulty = task_input.get("difficulty", 0.5)
        if self._object_level.should_decompose(difficulty):
            self._object_level.record_step(
                action="decompose",
                outcome=StepOutcome.SUCCESS,
                heuristic_applied="decompose_first",
                output_summary=f"Decomposing task (depth={genome.decomposition_depth})",
            )

        # Step 2: Tool selection (guided by strategy)
        for tool_name in genome.tool_priority[:3]:  # Try top-3 tools
            start = time.monotonic()
            try:
                if self.tools.has(tool_name):
                    result = await self.use_tool(tool_name, objective=objective, **task_input)
                    duration = (time.monotonic() - start) * 1000

                    self._object_level.record_step(
                        action=f"use_tool:{tool_name}",
                        outcome=StepOutcome.SUCCESS,
                        tool_used=tool_name,
                        duration_ms=duration,
                        output_summary=str(result)[:200] if result else "",
                    )
                    return {"tool": tool_name, "result": result}
                else:
                    self._object_level.record_step(
                        action=f"tool_lookup:{tool_name}",
                        outcome=StepOutcome.SKIPPED,
                        tool_used=tool_name,
                        output_summary=f"Tool '{tool_name}' not available",
                    )
            except Exception as exc:  # noqa: BLE001
                duration = (time.monotonic() - start) * 1000
                self._object_level.record_step(
                    action=f"use_tool:{tool_name}",
                    outcome=StepOutcome.FAILURE,
                    tool_used=tool_name,
                    error=repr(exc),
                    duration_ms=duration,
                )

                # Check escalation after each failure
                if self._object_level.should_escalate():
                    raise RuntimeError(
                        f"Escalation threshold reached after tool '{tool_name}' failure"
                    ) from exc

        # Step 3: Verification (if verify_before_emit heuristic is active)
        verify_h = None
        for h in genome.heuristics:
            if h.name == "verify_before_emit":
                verify_h = h
                break

        if verify_h and verify_h.weight > 0.5:
            self._object_level.record_step(
                action="verify",
                outcome=StepOutcome.SUCCESS,
                heuristic_applied="verify_before_emit",
                output_summary="Verification pass (no tools executed)",
            )

        return {
            "status": "completed",
            "note": "base execution — override _run_object_level for domain logic",
        }

    # ── Self-Assessment ──────────────────────────────────────────

    def _self_assess_confidence(self, outcome: StepOutcome) -> float:
        """Assess confidence in the result.

        Uses historical performance + current outcome to calibrate.
        """
        base = 0.7 if outcome == StepOutcome.SUCCESS else 0.3

        # Calibrate based on recent trace history
        recent_traces = self._object_level.trace_archive[-10:]
        if recent_traces:
            recent_success_rate = sum(
                1 for t in recent_traces if t.final_outcome == StepOutcome.SUCCESS
            ) / len(recent_traces)
            # Blend base with historical calibration
            calibrated = base * 0.6 + recent_success_rate * 0.4
        else:
            calibrated = base

        # Apply confidence anchoring heuristic if active
        for h in self._strategy.genome.heuristics:
            if h.name == "confidence_anchoring" and h.weight > 0.3:
                calibrated *= 0.7  # Reduce by 30% as prescribed
                break

        return min(1.0, max(0.0, calibrated))

    def _revise_output(
        self,
        result: dict[str, Any],
        judgment: MetaJudgment,
    ) -> dict[str, Any]:
        """Revise output to address structural constitutional violations."""
        revised = dict(result)
        revised["_sica_revised"] = True
        revised["_revision_reason"] = judgment.diagnosis

        if judgment.constitutional_verdict:
            for v in judgment.constitutional_verdict.structural_violations:
                revised.setdefault("_constitutional_notes", []).append(
                    f"[{v.principle.id}] {v.explanation}"
                )

        return revised

    # ── Message Emission ─────────────────────────────────────────

    async def _emit_result(
        self,
        original_msg: AgentMessage,
        task_id: str,
        result: dict[str, Any],
        judgment: MetaJudgment,
    ) -> None:
        """Emit a successful result with meta-annotations."""
        result["_sica_meta"] = {
            "genome_hash": self._strategy.genome.genome_hash,
            "genome_generation": self._strategy.genome.generation,
            "confidence": judgment.confidence,
            "mutations_applied": self._strategy.genome.generation,
        }
        await self.send_result(
            recipient=original_msg.sender,
            result=result,
            correlation_id=original_msg.correlation_id,
        )
        self._lifetime_stats.tasks_succeeded += 1

    async def _emit_failure(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment | None,
    ) -> None:
        """Emit a task failure with diagnostic metadata."""
        payload = {
            "task_id": task_id,
            "error": judgment.diagnosis if judgment else "Unknown failure",
            "retryable": False,
            "_sica_meta": {
                "failure_class": judgment.failure_class.value
                if judgment and judgment.failure_class
                else None,
                "is_meta_failure": judgment.is_meta_failure if judgment else False,
                "genome_hash": self._strategy.genome.genome_hash,
            },
        }
        msg = new_message(
            sender=self.agent_id,
            recipient=original_msg.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.bus.send(msg)
        self._lifetime_stats.tasks_failed += 1

    async def _emit_escalation(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment,
    ) -> None:
        """Escalate to human/supervisor with full diagnostic context."""
        payload = {
            "task_id": task_id,
            "escalation": True,
            "diagnosis": judgment.diagnosis,
            "reasoning_chain": judgment.reasoning_chain,
            "introspection": self._meta_level.introspect(),
        }
        msg = new_message(
            sender=self.agent_id,
            recipient="supervisor",
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.bus.send(msg)
        self._lifetime_stats.escalations += 1

    async def _emit_abort(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment,
    ) -> None:
        """Emit constitutional abort — the nuclear option."""
        logger.error(
            "[%s] CONSTITUTIONAL ABORT: %s",
            self.agent_id,
            judgment.diagnosis,
        )
        payload = {
            "task_id": task_id,
            "abort": True,
            "cardinal_violations": [
                str(v.principle)
                for v in (
                    judgment.constitutional_verdict.cardinal_violations
                    if judgment.constitutional_verdict
                    else []
                )
            ],
            "diagnosis": judgment.diagnosis,
        }
        msg = new_message(
            sender=self.agent_id,
            recipient=original_msg.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.bus.send(msg)
        self._lifetime_stats.aborts += 1

    # ── Introspection API ────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Full introspection of the SICA agent's cognitive state.

        Returns the complete meta-level report plus lifetime stats.
        """
        return {
            "agent_id": self.agent_id,
            "meta_level": self._meta_level.introspect(),
            "lifetime": self._lifetime_stats.to_dict(),
            "object_level": {
                "traces_archived": len(self._object_level.trace_archive),
                "last_trace": (
                    self._object_level.last_trace.to_dict()
                    if self._object_level.last_trace
                    else None
                ),
            },
        }


class _LifetimeStats:
    """Accumulated statistics across the agent's lifetime."""

    def __init__(self) -> None:
        self.tasks_succeeded = 0
        self.tasks_failed = 0
        self.escalations = 0
        self.aborts = 0
        self.mutations = 0
        self.meta_failures = 0
        self.object_failures = 0

    def record_judgment(self, judgment: MetaJudgment) -> None:
        if judgment.is_meta_failure:
            self.meta_failures += 1
        elif judgment.failure_class is not None:
            self.object_failures += 1

    def summary(self) -> str:
        total = self.tasks_succeeded + self.tasks_failed
        rate = (self.tasks_succeeded / total * 100) if total > 0 else 0
        return (
            f"tasks={total} success={rate:.0f}% "
            f"mutations={self.mutations} "
            f"meta_failures={self.meta_failures} "
            f"escalations={self.escalations}"
        )

    def to_dict(self) -> dict[str, Any]:
        total = self.tasks_succeeded + self.tasks_failed
        return {
            "total_tasks": total,
            "succeeded": self.tasks_succeeded,
            "failed": self.tasks_failed,
            "success_rate": round(self.tasks_succeeded / total, 3) if total > 0 else 0,
            "mutations": self.mutations,
            "meta_failures": self.meta_failures,
            "object_failures": self.object_failures,
            "escalations": self.escalations,
            "aborts": self.aborts,
        }
