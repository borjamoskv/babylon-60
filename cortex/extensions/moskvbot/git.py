"""Git helpers for MOSKVBot worktree isolation."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cortex.extensions.moskvbot.models import MOSKVBotError


class GitCommandError(MOSKVBotError):
    """Raised when a Git command fails."""


class GitClient:
    """Small wrapper around Git with deterministic error messages."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = self.resolve_repo_root(repo_path)

    @staticmethod
    def resolve_repo_root(repo_path: str | Path) -> Path:
        """Resolve the top-level Git repository path."""
        path = Path(repo_path).expanduser().resolve()
        result = GitClient._run_raw(["git", "-C", str(path), "rev-parse", "--show-toplevel"])
        return Path(result.stdout.strip()).resolve()

    @staticmethod
    def _run_raw(
        argv: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        try:
            result = subprocess.run(
                argv,
                cwd=str(cwd) if cwd else None,
                env=merged_env,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitCommandError(f"Git command timed out: {' '.join(argv)}") from exc
        except OSError as exc:
            raise GitCommandError(f"Git command could not start: {exc}") from exc

        if check and result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise GitCommandError(f"Git command failed ({result.returncode}): {stderr}")
        return result

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a Git command against the repository."""
        git_cwd = cwd or self.repo_path
        return self._run_raw(
            ["git", "-C", str(git_cwd), *args],
            env=env,
            timeout_s=timeout_s,
            check=check,
        )

    def current_branch(self) -> str:
        """Return the current branch name, or HEAD for detached checkouts."""
        result = self.run(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def head_sha(self) -> str:
        """Return the current HEAD SHA."""
        result = self.run(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def dirty_files(self, *, cwd: Path | None = None) -> tuple[str, ...]:
        """Return porcelain status entries for changed files."""
        result = self.run(["status", "--porcelain"], cwd=cwd, check=True)
        return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())

    def add_worktree(self, branch_name: str, worktree_path: Path) -> None:
        """Create a new branch-backed worktree at HEAD."""
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        self.run(["worktree", "add", "-b", branch_name, str(worktree_path), "HEAD"], timeout_s=60.0)

    def remove_worktree(
        self,
        branch_name: str,
        worktree_path: Path,
        *,
        delete_branch: bool = True,
    ) -> None:
        """Remove a worktree and optionally delete its temporary branch."""
        self.run(
            ["worktree", "remove", "--force", str(worktree_path)],
            timeout_s=60.0,
            check=False,
        )
        if delete_branch:
            self.run(["branch", "-D", branch_name], timeout_s=30.0, check=False)

    def commit_all(self, worktree_path: Path, message: str) -> str | None:
        """Commit all changed files in a worktree and return the new SHA."""
        if not self.dirty_files(cwd=worktree_path):
            return None
        env = {
            "GIT_AUTHOR_NAME": "MOSKVBot",
            "GIT_AUTHOR_EMAIL": "moskvbot@local.invalid",
            "GIT_COMMITTER_NAME": "MOSKVBot",
            "GIT_COMMITTER_EMAIL": "moskvbot@local.invalid",
        }
        self.run(["add", "-A"], cwd=worktree_path, env=env)
        self.run(["commit", "-m", message], cwd=worktree_path, env=env, timeout_s=60.0)
        result = self.run(["rev-parse", "HEAD"], cwd=worktree_path)
        return result.stdout.strip()


def sanitize_branch_component(value: str) -> str:
    """Convert free text into a conservative branch-name component."""
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower())
    normalized = normalized.strip("-._")
    return normalized[:48] or "mission"


@contextmanager
def git_worktree(
    repo_path: str | Path,
    *,
    branch_name: str,
    base_path: str | Path | None = None,
    keep: bool = True,
    delete_branch_on_cleanup: bool = True,
) -> Iterator[Path]:
    """Create a real Git worktree and clean it up unless keep is true."""
    git = GitClient(repo_path)
    base_dir = Path(base_path).expanduser() if base_path else Path.home() / ".cortex" / "moskvbot"
    safe_branch = branch_name.replace("/", "_")
    worktree_path = (base_dir / safe_branch).resolve()

    git.add_worktree(branch_name, worktree_path)
    try:
        yield worktree_path
    finally:
        if not keep:
            git.remove_worktree(
                branch_name,
                worktree_path,
                delete_branch=delete_branch_on_cleanup,
            )
