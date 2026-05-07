# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""Auto-remediation registry for health metrics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FixAction:
    """Registered remediation callable for a degraded health metric."""

    metric: str
    label: str
    fn: Callable[..., Any]
    risk: str = "medium"


class FixRegistry:
    """Maps degraded health metrics to explicit remediation actions."""

    def __init__(self) -> None:
        self._actions: dict[str, FixAction] = {}

    def register(
        self,
        metric: str,
        label: str,
        fn: Callable[..., Any],
        *,
        risk: str = "medium",
    ) -> None:
        """Register or replace a fix for a health metric."""
        self._actions[metric] = FixAction(metric=metric, label=label, fn=fn, risk=risk)

    def applicable_fixes(self, metrics: list[str]) -> list[FixAction]:
        """Return registered fixes matching degraded metric names."""
        return [self._actions[name] for name in metrics if name in self._actions]

    def list_fixable(self) -> list[str]:
        """List metric names with registered fixes."""
        return list(self._actions)
