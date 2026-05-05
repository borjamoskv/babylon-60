"""Gate Enums."""

from enum import Enum

__all__ = ["ActionLevel", "GatePolicy", "ActionStatus", "OversightState"]


class ActionLevel(str, Enum):
    """Consciousness layer action levels."""

    L1_READ = "L1_READ"
    L2_PLAN = "L2_PLAN"
    L3_EXECUTE = "L3_EXECUTE"
    L4_MUTATE = "L4_MUTATE"


class GatePolicy(str, Enum):
    """Gate enforcement policy."""

    ENFORCE = "enforce"  # Block until approved
    AUDIT_ONLY = "audit"  # Log but don't block
    DISABLED = "disabled"  # Transparent passthrough


class ActionStatus(str, Enum):
    """Status of a pending action."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


class OversightState(str, Enum):
    """Human-oversight lifecycle for regulated or high-risk actions."""

    MACHINE_RECOMMENDATION = "machine_recommendation"
    REVIEW_REQUIRED = "review_required"
    HUMAN_REVIEWED = "human_reviewed"
    HUMAN_OVERRIDE = "human_override"
    FINAL_EFFECT_EXECUTED = "final_effect_executed"
