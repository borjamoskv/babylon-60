from decimal import Decimal
from enum import Enum


class AgentMode(str, Enum):
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    DECORATIVE = "DECORATIVE"
    ACTIVE = "ACTIVE"


class ThermodynamicCounters:
    """Tracks exergy and thermodynamic metrics for decorative mode detection."""

    def __init__(
        self,
        *,
        consecutive_tool_fails_without_new_hypothesis: int = 0,
        file_reads_without_ast_delta: int = 0,
        context_expansion_rate: Decimal = Decimal("0.0"),
        uncertainty_reduction_rate: Decimal = Decimal("0.0"),
        total_exergy: Decimal = Decimal("0.0"),
        total_waste: Decimal = Decimal("0.0"),
        violations: int = 0,
    ) -> None:
        self.consecutive_tool_fails_without_new_hypothesis = consecutive_tool_fails_without_new_hypothesis
        self.file_reads_without_ast_delta = file_reads_without_ast_delta
        self.context_expansion_rate = context_expansion_rate
        self.uncertainty_reduction_rate = uncertainty_reduction_rate
        self.total_exergy = total_exergy
        self.total_waste = total_waste
        self.violations = violations


_TOOL_FAIL_THRESHOLD = 3
_FILE_READ_THRESHOLD = 5


def should_enter_decorative_mode(
    counters: ThermodynamicCounters,
) -> tuple[bool, list[str]]:
    """Returns (triggered, reasons) for decorative mode detection.

    Conditions:
      - consecutive_tool_fails_without_new_hypothesis >= 3
      - file_reads_without_ast_delta >= 5
      - context_expansion_rate > uncertainty_reduction_rate
    """
    reasons: list[str] = []

    if counters.consecutive_tool_fails_without_new_hypothesis >= _TOOL_FAIL_THRESHOLD:
        reasons.append(
            f"tool_fails_without_new_hypothesis>={_TOOL_FAIL_THRESHOLD}"
        )

    if counters.file_reads_without_ast_delta >= _FILE_READ_THRESHOLD:
        reasons.append(
            f"file_reads_without_ast_delta>={_FILE_READ_THRESHOLD}"
        )

    if counters.context_expansion_rate > counters.uncertainty_reduction_rate:
        reasons.append("context_expansion_rate>uncertainty_reduction_rate")

    return bool(reasons), reasons
