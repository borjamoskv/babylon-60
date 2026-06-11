# [C5-REAL] Exergy-Maximized
"""SICA Meta-Level - Metacognitive Monitor & Controller.

Nelson-Narens (1990) implementation:
  MONITOR (bottom-up): observes ExecutionTraces from the object-level
  CONTROL (top-down): mutates SearchStrategy based on diagnostic judgments

The critical insight: the meta-level distinguishes between:
  1. "The task failed" → adjust parameters, retry
  2. "My APPROACH to the task was wrong" → mutate the strategy genome

This is the qualitative leap - not just error detection, but
analysis of the agent's own cognitive processes.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.sica.constitution import Constitution
from cortex.sica.object_level import ExecutionTrace, StepOutcome
from cortex.sica.strategy import Heuristic, SearchStrategy, StrategyMutation
from cortex.sica.meta_types import FailureClass, MetaAction, MetaJudgment
from cortex.sica.meta_helpers import run_failure_checks, create_templated_heuristic

logger = logging.getLogger("cortex.sica.meta_level")


class MetaLevel:
    """The metacognitive engine.

    Implements the Nelson-Narens dual-process:
      - monitor(): bottom-up observation of execution traces
      - control(): top-down mutation of strategy genome

    The meta-level maintains its own judgment history to detect
    meta-meta patterns (e.g., "I keep misdiagnosing cascade failures").
    """

    def __init__(
        self,
        strategy: SearchStrategy,
        constitution: Constitution | None = None,
    ) -> None:
        self._strategy = strategy
        self._constitution = constitution or Constitution()
        self._judgment_history: list[MetaJudgment] = []
        self._mutation_history: list[StrategyMutation] = []

        # Meta-meta tracking: patterns in the meta-level's own behavior
        self._meta_error_count = 0
        self._consecutive_no_actions = 0

    @property
    def strategy(self) -> SearchStrategy:
        return self._strategy

    @property
    def constitution(self) -> Constitution:
        return self._constitution

    @property
    def judgment_history(self) -> list[MetaJudgment]:
        return list(self._judgment_history)

    # ── MONITOR (bottom-up) ──────────────────────────────────────

    def monitor(self, trace: ExecutionTrace) -> MetaJudgment:
        """Analyze an execution trace and produce a meta-judgment.

        This is the MONITOR function from Nelson-Narens.
        Information flows bottom-up: object-level → meta-level.
        """
        judgment = MetaJudgment(trace_id=trace.task_id)
        reasoning: list[str] = []

        # Phase 1: Constitutional evaluation
        output_repr = trace.to_dict()
        verdict = self._constitution.evaluate(output_repr)
        judgment.constitutional_verdict = verdict

        if verdict.abort_needed:
            judgment.failure_class = FailureClass.CONFIDENCE_MISCALIBRATION
            judgment.is_meta_failure = True
            judgment.diagnosis = "Constitutional cardinal violation - abort required."
            judgment.recommended_actions = [MetaAction.ESCALATE_TO_HUMAN]
            judgment.confidence = 0.95
            reasoning.append("CARDINAL violation detected → immediate escalation")
            judgment.reasoning_chain = reasoning
            self._judgment_history.append(judgment)
            return judgment

        # Phase 2: Success path - strategy reinforcement
        if trace.final_outcome == StepOutcome.SUCCESS:
            reasoning.append(f"Task succeeded (success_rate={trace.success_rate:.2f})")
            judgment = self._analyze_success(trace, judgment, reasoning)
            judgment.reasoning_chain = reasoning
            self._judgment_history.append(judgment)
            self._consecutive_no_actions = 0
            return judgment

        # Phase 3: Failure diagnosis - the core metacognitive analysis
        reasoning.append(f"Task failed (success_rate={trace.success_rate:.2f})")

        # Detect error pattern
        pattern = trace.error_pattern or trace.detect_error_pattern()
        if pattern:
            reasoning.append(f"Error pattern detected: {pattern}")

        # Classify the failure
        judgment = self._classify_failure(trace, judgment, reasoning)
        judgment.reasoning_chain = reasoning
        self._judgment_history.append(judgment)

        # Meta-meta check: are we stuck in a diagnosis loop?
        self._check_meta_patterns(judgment)

        return judgment

    def _analyze_success(
        self,
        trace: ExecutionTrace,
        judgment: MetaJudgment,
        reasoning: list[str],
    ) -> MetaJudgment:
        """Analyze a successful trace to reinforce good strategies."""
        judgment.failure_class = None
        judgment.is_meta_failure = False
        judgment.confidence = 0.8

        # Reinforce heuristics that were used
        heuristics_used = trace.heuristics_activated
        if heuristics_used:
            reasoning.append(f"Reinforcing heuristics: {heuristics_used}")
            judgment.recommended_actions = [MetaAction.AMPLIFY_HEURISTIC]
            judgment.diagnosis = (
                f"Success via heuristics [{', '.join(heuristics_used)}]. Reinforcing weights."
            )
        else:
            judgment.recommended_actions = [MetaAction.NO_ACTION]
            judgment.diagnosis = "Success without tracked heuristic activation."

        # If success was slow (>80% of steps), consider optimization
        if trace.success_rate < 0.6 and trace.final_outcome == StepOutcome.SUCCESS:
            reasoning.append("Success was inefficient - many failed intermediate steps")
            judgment.recommended_actions.append(MetaAction.ADJUST_DECOMPOSITION)

        return judgment

    def _classify_failure(
        self,
        trace: ExecutionTrace,
        judgment: MetaJudgment,
        reasoning: list[str],
    ) -> MetaJudgment:
        """Classify a failure as object-level or meta-level."""
        pattern = trace.error_pattern
        exploration_rate = self._strategy.genome.exploration_rate

        res = run_failure_checks(trace, pattern, judgment, reasoning, exploration_rate)
        if res:
            return res

        # Default: object-level failure (not a thinking error)
        failures = trace.failure_steps
        if failures:
            first_error = failures[0].error or "unknown"
            if "timeout" in first_error.lower():
                judgment.failure_class = FailureClass.TIMEOUT
            elif "not found" in first_error.lower() or "missing" in first_error.lower():
                judgment.failure_class = FailureClass.RESOURCE_MISSING
            elif "invalid" in first_error.lower() or "malformed" in first_error.lower():
                judgment.failure_class = FailureClass.INPUT_MALFORMED
            else:
                judgment.failure_class = FailureClass.TOOL_ERROR
        else:
            judgment.failure_class = FailureClass.TOOL_ERROR

        judgment.is_meta_failure = False
        judgment.diagnosis = (
            f"Object-level failure ({judgment.failure_class.value}). "
            f"The thinking approach was sound, but execution encountered an error."
        )
        judgment.recommended_actions = [MetaAction.NO_ACTION]
        judgment.confidence = 0.6
        reasoning.append(f"OBJECT-LEVEL failure: {judgment.failure_class.value}")
        return judgment

    # ── CONTROL (top-down) ───────────────────────────────────────

    def control(self, judgment: MetaJudgment) -> list[StrategyMutation]:
        """Execute control actions based on a meta-judgment.

        This is the CONTROL function from Nelson-Narens.
        Information flows top-down: meta-level → object-level strategy.

        Returns the list of mutations applied.
        """
        mutations: list[StrategyMutation] = []

        if not judgment.requires_strategy_mutation:
            self._consecutive_no_actions += 1
            return mutations

        self._consecutive_no_actions = 0

        for action in judgment.recommended_actions:
            mutation = self._execute_action(action, judgment)
            if mutation is not None:
                mutations.append(mutation)
                self._mutation_history.append(mutation)

        # Record fitness after mutations
        self._strategy.record_fitness()

        logger.info(
            "MetaLevel CONTROL: applied %d mutations (genome gen=%d, hash=%s)",
            len(mutations),
            self._strategy.genome.generation,
            self._strategy.genome.genome_hash,
        )
        return mutations

    def _execute_action(
        self,
        action: MetaAction,
        judgment: MetaJudgment,
    ) -> StrategyMutation | None:
        """Execute a single meta-action on the strategy."""
        handlers = {
            MetaAction.AMPLIFY_HEURISTIC: self._action_amplify,
            MetaAction.ATTENUATE_HEURISTIC: self._action_attenuate,
            MetaAction.INJECT_HEURISTIC: self._action_inject,
            MetaAction.PRUNE_HEURISTIC: self._action_prune,
            MetaAction.ADJUST_EXPLORATION: self._action_adjust_exploration,
            MetaAction.ADJUST_DECOMPOSITION: self._action_adjust_decomposition,
            MetaAction.FORCE_TOOL_SWITCH: self._action_force_tool_switch,
        }
        handler = handlers.get(action)
        return handler(judgment) if handler else None

    def _action_amplify(self, judgment: MetaJudgment) -> StrategyMutation | None:
        best = self._strategy.genome.dominant_heuristic
        if best and best.fitness > 0.5:
            return self._strategy.mutate_amplify(
                best.name, reason=f"Reinforcement after success: {judgment.diagnosis[:80]}"
            )
        return None

    def _action_attenuate(self, judgment: MetaJudgment) -> StrategyMutation | None:
        active = self._strategy.genome.active_heuristics
        if active:
            worst = min(active, key=lambda h: h.fitness)
            return self._strategy.mutate_attenuate(
                worst.name, reason=f"Attenuation after failure: {judgment.diagnosis[:80]}"
            )
        return None

    def _action_inject(self, judgment: MetaJudgment) -> StrategyMutation | None:
        new_h = self._synthesize_heuristic(judgment)
        if new_h is not None:
            fc_val = judgment.failure_class.value if judgment.failure_class else "unknown"
            return self._strategy.mutate_inject(new_h, reason=f"Injection to address: {fc_val}")
        return None

    def _action_prune(self, judgment: MetaJudgment) -> StrategyMutation | None:
        for h in self._strategy.genome.heuristics:
            if h.fitness < 0.1 and h.activation_count > 5:
                return self._strategy.mutate_prune(
                    h.name,
                    reason=f"Pruned dead heuristic (fitness={h.fitness:.3f}, activations={h.activation_count})",
                )
        return None

    def _action_adjust_exploration(self, judgment: MetaJudgment) -> StrategyMutation | None:
        current = self._strategy.genome.exploration_rate
        new_rate = min(0.8, current + 0.15)
        fc_val = judgment.failure_class.value if judgment.failure_class else "failure"
        self._strategy.mutate_exploration_rate(
            new_rate, reason=f"Increasing exploration after {fc_val}"
        )
        return None

    def _action_adjust_decomposition(self, judgment: MetaJudgment) -> StrategyMutation | None:
        self._strategy.genome.decomposition_depth = min(
            8, self._strategy.genome.decomposition_depth + 1
        )
        logger.info(
            "MetaLevel: decomposition depth → %d", self._strategy.genome.decomposition_depth
        )
        return None

    def _action_force_tool_switch(self, judgment: MetaJudgment) -> StrategyMutation | None:
        if len(self._strategy.genome.tool_priority) > 1:
            tools = self._strategy.genome.tool_priority
            tools.append(tools.pop(0))
            logger.info("MetaLevel: tool priority rotated → %s", tools)
        return None

    def _synthesize_heuristic(self, judgment: MetaJudgment) -> Heuristic | None:
        """Synthesize a new heuristic to address a diagnosed failure."""
        fc = judgment.failure_class
        if fc is None:
            return None

        new_h = create_templated_heuristic(fc)
        if new_h is None:
            return None

        # Check if this heuristic already exists
        existing_names = {h.name for h in self._strategy.genome.heuristics}
        if new_h.name in existing_names:
            return None  # Don't duplicate

        return new_h

    # ── Meta-Meta Analysis ───────────────────────────────────────

    def _check_meta_patterns(self, judgment: MetaJudgment) -> None:
        """Detect patterns in the meta-level's OWN behavior.

        This is the recursive depth: monitoring the monitor.
        """
        recent = self._judgment_history[-10:]

        # Pattern: consecutive NO_ACTION despite failures
        if self._consecutive_no_actions >= 5:
            logger.warning(
                "META-META: %d consecutive NO_ACTION judgments - "
                "meta-level may be blind to a systemic issue",
                self._consecutive_no_actions,
            )
            self._meta_error_count += 1

        # Pattern: all recent judgments have same failure class
        if len(recent) >= 5:
            classes = [j.failure_class for j in recent if j.failure_class is not None]
            if classes and len(set(classes)) == 1:
                logger.warning(
                    "META-META: Last %d judgments all classify as %s - "
                    "possible diagnostic tunnel vision",
                    len(classes),
                    classes[0].value,
                )
                self._meta_error_count += 1

        # Pattern: mutations not improving fitness
        if len(self._mutation_history) >= 5:
            recent_mutations = self._mutation_history[-5:]
            deltas = [m.fitness_delta for m in recent_mutations if m.fitness_delta is not None]
            if deltas and all(d <= 0 for d in deltas):
                logger.warning(
                    "META-META: Last %d mutations all had non-positive fitness delta - "
                    "meta-level control strategy may be wrong",
                    len(deltas),
                )
                self._meta_error_count += 1

    def introspect(self) -> dict[str, Any]:
        """Full introspection report of the meta-level's state.

        Returns a snapshot of:
          - Current strategy genome
          - Judgment history summary
          - Mutation history
          - Meta-meta error count
          - Constitutional violation history
        """
        recent_judgments = self._judgment_history[-20:]
        meta_failures = sum(1 for j in recent_judgments if j.is_meta_failure)
        obj_failures = sum(
            1 for j in recent_judgments if j.failure_class is not None and not j.is_meta_failure
        )

        return {
            "strategy": self._strategy.genome.to_dict(),
            "current_fitness": round(self._strategy.current_fitness, 4),
            "total_judgments": len(self._judgment_history),
            "recent_meta_failures": meta_failures,
            "recent_object_failures": obj_failures,
            "total_mutations": len(self._mutation_history),
            "meta_meta_errors": self._meta_error_count,
            "consecutive_no_actions": self._consecutive_no_actions,
            "constitutional_violations": len(self._constitution.violation_history),
            "genome_generation": self._strategy.genome.generation,
            "genome_hash": self._strategy.genome.genome_hash,
        }
