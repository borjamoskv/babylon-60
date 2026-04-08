"""Regression tests for Sovereign Seal helpers."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

from cortex.guards import sovereign_seals


def _completed_process(*, returncode: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
    """Build a lightweight subprocess result for monkeypatched git calls."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


@pytest.mark.asyncio
async def test_gate_21_uses_git_resolved_hook_path_for_worktrees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seal 10 must honor git's resolved hook path when `.git` is a worktree file."""
    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    (worktree_root / ".git").write_text("gitdir: /external/gitdir\n", encoding="utf-8")

    seals_path = worktree_root / "cortex" / "guards" / "seals.py"
    seals_path.parent.mkdir(parents=True)
    seals_path.write_text("# test sentinel\n", encoding="utf-8")

    hook_path = tmp_path / "canonical-hooks" / "pre-push"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)

    def _fake_run(
        args: list[str], *, cwd: str, capture_output: bool, text: bool, timeout: int
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == str(worktree_root)
        assert capture_output is True
        assert text is True
        assert timeout == 5

        if args == ["git", "rev-parse", "--git-path", "hooks/pre-push"]:
            return _completed_process(returncode=0, stdout=f"{hook_path}\n")
        if args == ["git", "rev-parse", "HEAD~1"]:
            return _completed_process(returncode=0, stdout="deadbeef\n")
        raise AssertionError(f"Unexpected subprocess invocation: {args!r}")

    monkeypatch.setattr(sovereign_seals, "ROOT_DIR", worktree_root)
    monkeypatch.setattr(sovereign_seals.subprocess, "run", _fake_run)

    passed, reason = await sovereign_seals.check_gate_21_preservation()

    assert passed is True
    assert reason == "verified"
