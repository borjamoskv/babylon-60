from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from cortex.cli import cli
from cortex.extensions.moskvbot import (
    CloudExecutionUnavailable,
    CommandSpec,
    ExecutionBackend,
    MOSKVBot,
    MOSKVBotPlanner,
    MissionStatus,
    WorkerSpec,
)


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    _run_git(repo, "config", "user.name", "Test User")
    _run_git(repo, "config", "user.email", "test@example.invalid")
    (repo / "pyproject.toml").write_text(
        """
[project]
name = "sample"

[project.scripts]
sample = "sample:main"
""".strip(),
        encoding="utf-8",
    )
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    return repo


def test_planner_builds_codebase_snapshot(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    planner = MOSKVBotPlanner(repo)

    plan = planner.build("Add MOSKVBot execution lane")

    assert plan.repo_path == repo
    assert plan.branch_name.startswith("codex/moskvbot/add-moskvbot-execution-lane-")
    assert plan.snapshot.language_counts["python"] == 1
    assert plan.snapshot.entrypoints == ("sample",)
    assert plan.validation_commands[0].display == "git diff --check"


def test_runner_executes_validates_and_commits_in_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    write_command = CommandSpec(
        (
            sys.executable,
            "-c",
            "from pathlib import Path; Path('generated.txt').write_text('ok\\n', encoding='utf-8')",
        )
    )
    validate_command = CommandSpec(
        (
            sys.executable,
            "-c",
            "from pathlib import Path; assert Path('generated.txt').read_text(encoding='utf-8') == 'ok\\n'",
        )
    )
    worker = WorkerSpec(
        worker_id="executor",
        role="coding-worker",
        objective="write generated file",
        commands=(write_command,),
    )
    planner = MOSKVBotPlanner(repo)
    plan = planner.build(
        "Generate a file",
        workers=(worker,),
        validation_commands=(validate_command,),
    )
    bot = MOSKVBot(repo)

    result = asyncio.run(
        bot.run(
            plan,
            commit=True,
            keep_worktree=True,
            worktree_base_path=tmp_path / "worktrees",
        )
    )

    assert result.status is MissionStatus.COMPLETED
    assert result.commit_sha is not None
    assert "?? generated.txt" in result.changed_files
    assert result.worktree_path is not None
    assert (result.worktree_path / "generated.txt").read_text(encoding="utf-8") == "ok\n"


def test_runner_fails_closed_for_cloud_backend(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    planner = MOSKVBotPlanner(repo)
    plan = planner.build("Cloud mission", backend=ExecutionBackend.CLOUD_ISOLATED)
    bot = MOSKVBot(repo)

    with pytest.raises(CloudExecutionUnavailable):
        asyncio.run(bot.run(plan, worktree_base_path=tmp_path / "worktrees"))


def test_runner_reports_command_start_failure(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    worker = WorkerSpec(
        worker_id="executor",
        role="coding-worker",
        objective="run missing command",
        commands=(CommandSpec(("moskvbot-command-that-does-not-exist",)),),
    )
    plan = MOSKVBotPlanner(repo).build(
        "Missing command",
        workers=(worker,),
        validation_commands=(),
    )
    result = asyncio.run(
        MOSKVBot(repo).run(
            plan,
            keep_worktree=False,
            worktree_base_path=tmp_path / "worktrees",
        )
    )

    assert result.status is MissionStatus.FAILED
    assert result.worktree_path is None
    assert result.command_results[0].return_code == -1
    assert "worker command failed" in result.errors[0]


def test_moskvbot_cli_is_registered() -> None:
    assert "moskvbot" in cli.commands

    result = CliRunner().invoke(cli, ["moskvbot", "plan", "Inspect repo", "--json"])

    assert result.exit_code == 0
    assert '"goal": "Inspect repo"' in result.output
