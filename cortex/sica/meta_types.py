# [C5-REAL] Exergy-Maximized
"""SICA Meta-Level Shared Types and Structures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex.sica.constitution import ConstitutionalVerdict


class FailureClass(str, Enum):
    """Classification of WHY something failed.

    The meta-level's primary job is to classify failures into
    these categories - each triggers a different control response.
    """

    # Object-level failures (fix the task)
    TOOL_ERROR = "tool_error"  # Tool returned error
    INPUT_MALFORMED = "input_malformed"  # Bad input to tool
    RESOURCE_MISSING = "resource_missing"  # Required resource unavailable
    TIMEOUT = "timeout"  # Ran out of time

    # Meta-level failures (fix the thinking)
    WRONG_DECOMPOSITION = "wrong_decomposition"  # Problem split incorrectly
    WRONG_TOOL_CHOICE = "wrong_tool_choice"  # Used wrong tool for the job
    WRONG_HEURISTIC = "wrong_heuristic"  # Applied wrong heuristic
    STALE_PATTERN = "stale_pattern"  # Used outdated solution pattern
    EXPLORATION_DEFICIT = "exploration_deficit"  # Stuck in local optimum
    CASCADE_BLINDNESS = "cascade_blindness"  # Kept going after clear failure signal
    CONFIDENCE_MISCALIBRATION = "confidence_miscalibration"  # Over/under-confident


class MetaAction(str, Enum):
    """Control actions the meta-level can take."""

    AMPLIFY_HEURISTIC = "amplify_heuristic"
    ATTENUATE_HEURISTIC = "attenuate_heuristic"
    INJECT_HEURISTIC = "inject_heuristic"
    PRUNE_HEURISTIC = "prune_heuristic"
    ADJUST_EXPLORATION = "adjust_exploration"
    ADJUST_DECOMPOSITION = "adjust_decomposition"
    FORCE_TOOL_SWITCH = "force_tool_switch"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    NO_ACTION = "no_action"


@dataclass
class MetaJudgment:
    """A meta-level judgment about an execution trace.

    This is the output of the MONITOR function - a structured
    diagnosis of what happened and why.
    """

    trace_id: str
    failure_class: FailureClass | None = None
    is_meta_failure: bool = False  # True = thinking failed, not just the task
    diagnosis: str = ""
    recommended_actions: list[MetaAction] = field(default_factory=list)
    constitutional_verdict: ConstitutionalVerdict | None = None
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.monotonic)

    # Causal chain: why did the meta-level reach this judgment?
    reasoning_chain: list[str] = field(default_factory=list)

    @property
    def requires_strategy_mutation(self) -> bool:
        """True if this judgment calls for strategy evolution."""
        return self.is_meta_failure or any(
            a
            in (
                MetaAction.AMPLIFY_HEURISTIC,
                MetaAction.ATTENUATE_HEURISTIC,
                MetaAction.INJECT_HEURISTIC,
                MetaAction.PRUNE_HEURISTIC,
                MetaAction.ADJUST_EXPLORATION,
            )
            for a in self.recommended_actions
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "is_meta_failure": self.is_meta_failure,
            "diagnosis": self.diagnosis,
            "actions": [a.value for a in self.recommended_actions],
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning_chain,
        }
