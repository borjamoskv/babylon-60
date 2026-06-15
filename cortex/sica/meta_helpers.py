# [C5-REAL] Exergy-Maximized
"""SICA Meta-Level Helpers."""

from __future__ import annotations

from typing import Any

from cortex.sica.meta_types import FailureClass, MetaAction, MetaJudgment
from cortex.sica.strategy import Heuristic


def run_failure_checks(
    trace: Any,
    pattern: str | None,
    judgment: MetaJudgment,
    reasoning: list[str],
    exploration_rate: float,
) -> MetaJudgment | None:
    """Classifies SICA failures and suggests meta actions."""
    if pattern == "cascade_failure":
        judgment.failure_class = FailureClass.CASCADE_BLINDNESS
        judgment.is_meta_failure = True
        judgment.diagnosis = (
            "Cascade failure detected: the agent continued executing after "
            "a clear failure signal. The STOP heuristic is too weak."
        )
        judgment.recommended_actions = [
            MetaAction.INJECT_HEURISTIC,
            MetaAction.ATTENUATE_HEURISTIC,
        ]
        judgment.confidence = 0.85
        reasoning.append("CASCADE BLINDNESS → meta-failure: thinking process deficient")
        return judgment

    if pattern and pattern.startswith("repeated_tool_failure:"):
        tool_name = pattern.split(":", 1)[1]
        judgment.failure_class = FailureClass.WRONG_TOOL_CHOICE
        judgment.is_meta_failure = True
        judgment.diagnosis = (
            f"Repeated failure with tool '{tool_name}'. The agent's tool selection "
            f"heuristic is miscalibrated - it keeps choosing a tool that doesn't work "
            f"for this problem class."
        )
        judgment.recommended_actions = [
            MetaAction.FORCE_TOOL_SWITCH,
            MetaAction.ATTENUATE_HEURISTIC,
            MetaAction.ADJUST_EXPLORATION,
        ]
        judgment.confidence = 0.8
        reasoning.append(f"WRONG TOOL CHOICE → meta-failure: tool '{tool_name}' repeatedly fails")
        return judgment

    if pattern and pattern.startswith("repeated_error:"):
        judgment.failure_class = FailureClass.STALE_PATTERN
        judgment.is_meta_failure = True
        judgment.diagnosis = (
            "Same error repeated across steps. The agent is applying a stale "
            "solution pattern that doesn't fit this problem."
        )
        judgment.recommended_actions = [
            MetaAction.PRUNE_HEURISTIC,
            MetaAction.ADJUST_EXPLORATION,
        ]
        judgment.confidence = 0.75
        reasoning.append("STALE PATTERN → meta-failure: outdated solution approach")
        return judgment

    if trace.self_assessed_confidence > 0.7:
        judgment.failure_class = FailureClass.CONFIDENCE_MISCALIBRATION
        judgment.is_meta_failure = True
        judgment.diagnosis = (
            f"Agent was {trace.self_assessed_confidence:.0%} confident but failed. "
            f"Confidence calibration is broken - the meta-monitoring itself "
            f"is unreliable."
        )
        judgment.recommended_actions = [
            MetaAction.ATTENUATE_HEURISTIC,
            MetaAction.INJECT_HEURISTIC,
        ]
        judgment.confidence = 0.7
        reasoning.append("CONFIDENCE MISCALIBRATION → meta-failure: broken self-assessment")
        return judgment

    if exploration_rate < 0.2:
        judgment.failure_class = FailureClass.EXPLORATION_DEFICIT
        judgment.is_meta_failure = True
        judgment.diagnosis = (
            "Exploration rate is very low and the agent is failing. "
            "Likely stuck in a local optimum - needs more diverse search."
        )
        judgment.recommended_actions = [MetaAction.ADJUST_EXPLORATION]
        judgment.confidence = 0.65
        reasoning.append("EXPLORATION DEFICIT → meta-failure: stuck in local optimum")
        return judgment

    return None


HEURISTIC_TEMPLATES: dict[FailureClass, tuple[str, str]] = {
    FailureClass.CASCADE_BLINDNESS: (
        "early_stop_on_cascade",
        "Halt execution after 2 consecutive failures on the same sub-problem. "
        "Do not continue blindly.",
    ),
    FailureClass.WRONG_TOOL_CHOICE: (
        "tool_diversity_forced",
        "After a tool fails twice, MUST switch to a different tool. "
        "Never retry the same tool more than twice.",
    ),
    FailureClass.STALE_PATTERN: (
        "novelty_seeking",
        "When a previously successful pattern fails, try a fundamentally "
        "different approach rather than minor variations.",
    ),
    FailureClass.CONFIDENCE_MISCALIBRATION: (
        "confidence_anchoring",
        "Reduce initial confidence by 30%. Only increase confidence after "
        "verification step succeeds.",
    ),
    FailureClass.EXPLORATION_DEFICIT: (
        "random_probe",
        "Periodically try a random tool/approach to escape local optima.",
    ),
}


def create_templated_heuristic(fc: FailureClass) -> Heuristic | None:
    """Creates a new Heuristic from pre-defined failure class templates."""
    template = HEURISTIC_TEMPLATES.get(fc)
    if template is None:
        return None
    name, description = template
    return Heuristic(name=name, description=description, weight=0.6)
