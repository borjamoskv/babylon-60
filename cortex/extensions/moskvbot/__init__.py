"""MOSKVBot coding-agent primitives.

The package is intentionally small: it provides typed mission plans, isolated
Git worktrees, parallel command execution, and optional Git commits. LLM or
cloud providers can plug into these boundaries without weakening local
deterministic validation.
"""

from __future__ import annotations

from cortex.extensions.moskvbot.models import (
    CloudExecutionUnavailable,
    CodebaseSnapshot,
    CommandResult,
    CommandSpec,
    ExecutionBackend,
    MissionPlan,
    MissionResult,
    MissionStatus,
    MOSKVBotError,
    WorkerSpec,
)
from cortex.extensions.moskvbot.planner import MOSKVBotPlanner
from cortex.extensions.moskvbot.runner import MOSKVBot

__all__ = [
    "CloudExecutionUnavailable",
    "CodebaseSnapshot",
    "CommandResult",
    "CommandSpec",
    "ExecutionBackend",
    "MOSKVBot",
    "MOSKVBotError",
    "MOSKVBotPlanner",
    "MissionPlan",
    "MissionResult",
    "MissionStatus",
    "WorkerSpec",
]
