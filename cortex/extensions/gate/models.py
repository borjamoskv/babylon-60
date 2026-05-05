"""
CORTEX v5.1 — SovereignGate Models.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .enums import ActionLevel, ActionStatus, GatePolicy, OversightState

__all__ = ["PendingAction", "GatePolicy"]


@dataclass
class PendingAction:
    """An L3 action awaiting operator approval."""

    action_id: str
    level: ActionLevel
    description: str
    command: Optional[list[str]] = None
    project: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    oversight_state: OversightState = OversightState.MACHINE_RECOMMENDATION
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    reviewed_at: Optional[float] = None
    overridden_at: Optional[float] = None
    executed_at: Optional[float] = None
    hmac_challenge: str = ""
    operator_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_role: Optional[str] = None
    reason_code: Optional[str] = None
    auth_method: Optional[str] = None
    strong_auth_token: Optional[str] = None
    override_reason_code: Optional[str] = None
    high_risk: bool = False
    requires_human_review: bool = False
    limitations: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    result: Optional[dict[str, Any]] = None

    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if the action has exceeded its timeout."""
        return time.time() - self.created_at > timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses and audit log."""
        return {
            "action_id": self.action_id,
            "level": self.level.value,
            "description": self.description,
            "command": self.command,
            "project": self.project,
            "status": self.status.value,
            "oversight_state": self.oversight_state.value,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "approved_at": (
                datetime.fromtimestamp(self.approved_at, tz=timezone.utc).isoformat()
                if self.approved_at
                else None
            ),
            "reviewed_at": (
                datetime.fromtimestamp(self.reviewed_at, tz=timezone.utc).isoformat()
                if self.reviewed_at
                else None
            ),
            "overridden_at": (
                datetime.fromtimestamp(self.overridden_at, tz=timezone.utc).isoformat()
                if self.overridden_at
                else None
            ),
            "operator_id": self.operator_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "reason_code": self.reason_code,
            "auth_method": self.auth_method,
            "high_risk": self.high_risk,
            "requires_human_review": self.requires_human_review,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }
