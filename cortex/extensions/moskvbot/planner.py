"""Deterministic MOSKVBot mission planning."""

from __future__ import annotations

import sys
import uuid
from collections import Counter
from pathlib import Path

from cortex.extensions.moskvbot.git import GitClient, sanitize_branch_component
from cortex.extensions.moskvbot.models import (
    CodebaseSnapshot,
    CommandSpec,
    ExecutionBackend,
    MissionPlan,
    WorkerSpec,
)

_LANGUAGE_SUFFIXES = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".sol": "solidity",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


class MOSKVBotPlanner:
    """Builds mission plans from repository facts, not free-form guesses."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.git = GitClient(repo_path)
        self.repo_path = self.git.repo_path

    def snapshot(self) -> CodebaseSnapshot:
        """Inspect the repository enough to route validation and worker scope."""
        files = self._tracked_files()
        language_counts: Counter[str] = Counter()
        test_files: list[str] = []
        entrypoints: list[str] = []

        for relative in files:
            suffix = Path(relative).suffix.lower()
            language = _LANGUAGE_SUFFIXES.get(suffix)
            if language:
                language_counts[language] += 1
            if relative.startswith("tests/") and Path(relative).name.startswith("test_"):
                test_files.append(relative)

        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            entrypoints.extend(self._read_pyproject_scripts(pyproject))

        return CodebaseSnapshot(
            repo_path=self.repo_path,
            head_sha=self.git.head_sha(),
            branch=self.git.current_branch(),
            dirty_files=self.git.dirty_files(),
            language_counts=dict(sorted(language_counts.items())),
            test_files=tuple(sorted(test_files)[:50]),
            entrypoints=tuple(sorted(entrypoints)),
        )

    def build(
        self,
        goal: str,
        *,
        backend: ExecutionBackend = ExecutionBackend.LOCAL_WORKTREE,
        workers: tuple[WorkerSpec, ...] = (),
        validation_commands: tuple[CommandSpec, ...] | None = None,
        branch_prefix: str = "codex/moskvbot",
    ) -> MissionPlan:
        """Build a runnable plan with conservative default validation."""
        mission_id = uuid.uuid4().hex[:10]
        clean_goal = sanitize_branch_component(goal)
        branch_name = f"{branch_prefix}/{clean_goal}-{mission_id}"
        snapshot = self.snapshot()
        validations = validation_commands
        if validations is None:
            validations = self.default_validation_commands(snapshot)

        if not workers:
            workers = (
                WorkerSpec(
                    worker_id="planner",
                    role="codebase-planner",
                    objective="Inspect the codebase and produce an implementation route.",
                    commands=(),
                    owns=(),
                ),
            )

        return MissionPlan(
            mission_id=mission_id,
            goal=goal,
            repo_path=self.repo_path,
            branch_name=branch_name,
            backend=backend,
            snapshot=snapshot,
            workers=workers,
            validation_commands=validations,
        )

    def default_validation_commands(
        self, snapshot: CodebaseSnapshot | None = None
    ) -> tuple[CommandSpec, ...]:
        """Return cheap validation that is safe as a default for large repos."""
        del snapshot
        return (CommandSpec(("git", "diff", "--check"), timeout_s=60.0),)

    def suggested_validation_commands(self, snapshot: CodebaseSnapshot) -> tuple[CommandSpec, ...]:
        """Return broader checks a caller can opt into for a coding mission."""
        commands = [CommandSpec(("git", "diff", "--check"), timeout_s=60.0)]
        if snapshot.language_counts.get("python"):
            commands.append(CommandSpec((sys.executable, "-m", "pytest", "-q"), timeout_s=300.0))
        if (self.repo_path / "pyproject.toml").exists():
            commands.append(CommandSpec((sys.executable, "-m", "ruff", "check", "cortex"), timeout_s=300.0))
        return tuple(commands)

    def _tracked_files(self) -> tuple[str, ...]:
        result = self.git.run(["ls-files"])
        return tuple(line for line in result.stdout.splitlines() if line)

    def _read_pyproject_scripts(self, pyproject: Path) -> list[str]:
        if sys.version_info < (3, 11):
            return []
        import tomllib

        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
        scripts = data.get("project", {}).get("scripts", {})
        if not isinstance(scripts, dict):
            return []
        return [str(name) for name in scripts]
