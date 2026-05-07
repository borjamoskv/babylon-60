"""Typed contracts for MOSKVBot missions."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class MOSKVBotError(RuntimeError):
    """Base error for MOSKVBot orchestration failures."""


class CloudExecutionUnavailable(MOSKVBotError):
    """Raised when cloud execution is requested without a configured adapter."""


class CommandValidationError(MOSKVBotError):
    """Raised when a command spec is unsafe or incomplete."""


class ExecutionBackend(str, Enum):
    """Execution backends supported by MOSKVBot."""

    LOCAL_WORKTREE = "local-worktree"
    CLOUD_ISOLATED = "cloud-isolated"


class MissionStatus(str, Enum):
    """Lifecycle states for a MOSKVBot mission."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class CommandSpec:
    """A command executed without a shell inside the mission workspace."""

    argv: tuple[str, ...]
    cwd: str | None = None
    timeout_s: float = 120.0
    allowed_exit_codes: tuple[int, ...] = (0,)
    redact: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.argv:
            raise CommandValidationError("Command argv must not be empty")
        if not self.argv[0].strip():
            raise CommandValidationError("Command executable must not be blank")
        if self.timeout_s <= 0:
            raise CommandValidationError("Command timeout must be positive")

    @classmethod
    def from_string(cls, command: str, *, timeout_s: float = 120.0) -> CommandSpec:
        """Parse a CLI string into argv without enabling shell execution."""
        argv = tuple(shlex.split(command))
        if not argv:
            raise CommandValidationError("Command string must not be empty")
        return cls(argv=argv, timeout_s=timeout_s)

    @property
    def display(self) -> str:
        """Return a shell-escaped display string for humans and JSON output."""
        return shlex.join(self.argv)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the command spec for CLI JSON output."""
        return {
            "argv": list(self.argv),
            "cwd": self.cwd,
            "timeout_s": self.timeout_s,
            "allowed_exit_codes": list(self.allowed_exit_codes),
        }


@dataclass(frozen=True)
class WorkerSpec:
    """A bounded worker lane in a coding mission."""

    worker_id: str
    role: str
    objective: str
    commands: tuple[CommandSpec, ...] = ()
    owns: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the worker spec for CLI JSON output."""
        return {
            "worker_id": self.worker_id,
            "role": self.role,
            "objective": self.objective,
            "owns": list(self.owns),
            "commands": [command.to_dict() for command in self.commands],
        }


@dataclass(frozen=True)
class CodebaseSnapshot:
    """Deterministic summary of the target repository at plan time."""

    repo_path: Path
    head_sha: str
    branch: str
    dirty_files: tuple[str, ...] = ()
    language_counts: dict[str, int] = field(default_factory=dict)
    test_files: tuple[str, ...] = ()
    entrypoints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot for CLI JSON output."""
        return {
            "repo_path": str(self.repo_path),
            "head_sha": self.head_sha,
            "branch": self.branch,
            "dirty_files": list(self.dirty_files),
            "language_counts": dict(self.language_counts),
            "test_files": list(self.test_files),
            "entrypoints": list(self.entrypoints),
        }


@dataclass(frozen=True)
class MissionPlan:
    """A runnable MOSKVBot coding mission."""

    mission_id: str
    goal: str
    repo_path: Path
    branch_name: str
    backend: ExecutionBackend
    snapshot: CodebaseSnapshot
    workers: tuple[WorkerSpec, ...] = ()
    validation_commands: tuple[CommandSpec, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plan for CLI JSON output."""
        return {
            "mission_id": self.mission_id,
            "goal": self.goal,
            "repo_path": str(self.repo_path),
            "branch_name": self.branch_name,
            "backend": self.backend.value,
            "snapshot": self.snapshot.to_dict(),
            "workers": [worker.to_dict() for worker in self.workers],
            "validation_commands": [command.to_dict() for command in self.validation_commands],
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CommandResult:
    """Result of one process execution."""

    command: CommandSpec
    cwd: Path
    return_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """Whether the command exited with an allowed return code."""
        return not self.timed_out and self.return_code in self.command.allowed_exit_codes

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for CLI JSON output."""
        return {
            "command": self.command.display,
            "cwd": str(self.cwd),
            "return_code": self.return_code,
            "ok": self.ok,
            "timed_out": self.timed_out,
            "duration_s": round(self.duration_s, 4),
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class MissionResult:
    """Final mission execution result."""

    mission_id: str
    status: MissionStatus
    worktree_path: Path | None
    branch_name: str
    command_results: tuple[CommandResult, ...] = ()
    validation_results: tuple[CommandResult, ...] = ()
    changed_files: tuple[str, ...] = ()
    commit_sha: str | None = None
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result for CLI JSON output."""
        return {
            "mission_id": self.mission_id,
            "status": self.status.value,
            "worktree_path": str(self.worktree_path) if self.worktree_path else None,
            "branch_name": self.branch_name,
            "commit_sha": self.commit_sha,
            "changed_files": list(self.changed_files),
            "errors": list(self.errors),
            "command_results": [result.to_dict() for result in self.command_results],
            "validation_results": [result.to_dict() for result in self.validation_results],
        }
