from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal


@dataclass(slots=True)
class GuardOutcome:
    guard_name: str
    allowed: bool
    severity: Literal["low", "medium", "high", "critical"]
    code: str
    reason: str
    meta: dict[str, Any] = field(default_factory=dict)


class GuardExecutionError(RuntimeError):
    """Raised when a required guard fails during evaluation."""


class GuardBlockedWrite(RuntimeError):
    """Raised when guard policy blocks the write-path."""


TelemetryHook = Callable[[GuardOutcome], None]


def enforce_guard_pipeline(
    guards: Iterable[Any],
    context: dict[str, Any],
    *,
    telemetry_hook: TelemetryHook | None = None,
) -> list[GuardOutcome]:
    """Execute guards with fail-closed semantics for required controls.

    Rules:
    - required guard exception => abort write-path
    - required guard blocked outcome => abort write-path
    - any high/critical blocked outcome => abort write-path
    - optional guard exception => ignore for availability, never authorizes a write
    """
    outcomes: list[GuardOutcome] = []

    for guard in guards:
        required = bool(getattr(guard, "required", False))
        guard_name = getattr(guard, "name", guard.__class__.__name__)

        try:
            outcome = guard.evaluate(context)
        except Exception as exc:
            if required:
                raise GuardExecutionError(f"Required guard failed: {guard_name}") from exc
            continue

        if telemetry_hook is not None:
            telemetry_hook(outcome)

        outcomes.append(outcome)

        if required and not outcome.allowed:
            raise GuardBlockedWrite(
                f"Required guard blocked write: {guard_name}: {outcome.reason}"
            )

        if (not outcome.allowed) and outcome.severity in {"high", "critical"}:
            raise GuardBlockedWrite(
                f"High-severity guard blocked write: {guard_name}: {outcome.reason}"
            )

    return outcomes


class BridgeConflictGuard:
    required = True
    name = "bridge_conflict_guard"

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        bridge_result = context.get("bridge_result") or {}
        allowed = bool(bridge_result.get("allowed", False))
        reason = str(bridge_result.get("reason", "bridge validation failed"))
        return GuardOutcome(
            guard_name=self.name,
            allowed=allowed,
            severity="high" if not allowed else "low",
            code="bridge.blocked" if not allowed else "bridge.allowed",
            reason=reason,
            meta={"meta_flags": bridge_result.get("meta_flags") or {}},
        )


class ContradictionSignalGuard:
    required = True
    name = "contradiction_signal_guard"

    def evaluate(self, context: dict[str, Any]) -> GuardOutcome:
        rejection = context.get("nemesis_rejection")
        if rejection:
            return GuardOutcome(
                guard_name=self.name,
                allowed=False,
                severity="high",
                code="contradiction.detected",
                reason=str(rejection),
            )
        return GuardOutcome(
            guard_name=self.name,
            allowed=True,
            severity="low",
            code="contradiction.clear",
            reason="no contradiction detected",
        )
