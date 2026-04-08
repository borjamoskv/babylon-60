"""Helpers for turning GitHub navigation tricks into repeatable commands."""

from __future__ import annotations

import re
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, quote_plus

__all__ = [
    "GitHubRepoContext",
    "GitHubShortcutError",
    "GitHubShortcutService",
    "parse_line_spec",
    "run_gh",
]

_LINE_SPEC_RE = re.compile(r"^(?P<start>\d+)(?:\s*[-:]\s*(?P<end>\d+))?$")
_SSH_REMOTE_RE = re.compile(r"^(?:ssh://)?git@(?P<host>[^/:]+)[:/](?P<slug>.+?)(?:\.git)?$")
_HTTPS_REMOTE_RE = re.compile(
    r"^https?://(?:(?:[^@/]+)@)?(?P<host>[^/]+)/(?P<slug>.+?)(?:\.git)?$"
)


class GitHubShortcutError(RuntimeError):
    """Raised when a GitHub shortcut cannot be resolved safely."""


@dataclass(frozen=True)
class GitHubRepoContext:
    """Resolved GitHub context for the current local repository."""

    repo_root: Path
    remote_name: str
    host: str
    owner: str
    repo: str
    branch: str
    head_sha: str

    @property
    def web_base_url(self) -> str:
        return f"https://{self.host}/{quote(self.owner, safe='')}/{quote(self.repo, safe='')}"

    @property
    def current_ref(self) -> str:
        if self.branch == "HEAD":
            return self.head_sha
        return self.branch

    @property
    def name_with_owner(self) -> str:
        return f"{self.owner}/{self.repo}"

    def dev_base_url(self) -> str:
        if self.host != "github.com":
            raise GitHubShortcutError("`github.dev` only supports repositories hosted on github.com.")
        return (
            "https://github.dev/"
            f"{quote(self.owner, safe='')}/{quote(self.repo, safe='')}"
        )


def parse_line_spec(line_spec: str | None) -> tuple[int | None, int | None]:
    """Parse a GitHub-style line selector like ``10`` or ``10-25``."""
    if line_spec is None:
        return None, None

    match = _LINE_SPEC_RE.fullmatch(line_spec.strip())
    if match is None:
        raise GitHubShortcutError(
            "Invalid line range. Use a single line like `10` or a range like `10-25`."
        )

    start = int(match.group("start"))
    end_value = match.group("end")
    end = int(end_value) if end_value is not None else start
    if start <= 0 or end <= 0:
        raise GitHubShortcutError("Line numbers must be positive integers.")
    if end < start:
        raise GitHubShortcutError("The ending line must be greater than or equal to the starting line.")
    return start, end


def _quote_path(path: str) -> str:
    return "/".join(quote(part, safe="") for part in path.split("/"))


def _quote_ref(ref: str) -> str:
    return quote(ref, safe="")


def _run_git(cwd: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            cwd=str(cwd),
            text=True,
        )
    except FileNotFoundError as err:
        raise GitHubShortcutError("`git` is required but was not found in PATH.") from err
    except subprocess.CalledProcessError as err:
        stderr = (err.stderr or "").strip()
        detail = stderr or "git command failed"
        raise GitHubShortcutError(detail) from err

    return completed.stdout.strip()


def _parse_remote_url(remote_url: str) -> tuple[str, str, str]:
    for pattern in (_SSH_REMOTE_RE, _HTTPS_REMOTE_RE):
        match = pattern.fullmatch(remote_url.strip())
        if match is None:
            continue
        slug = match.group("slug").strip("/")
        parts = slug.split("/")
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1]
            return match.group("host").lower(), owner, repo

    raise GitHubShortcutError(f"Unsupported GitHub remote URL: {remote_url}")


class GitHubShortcutService:
    """Build browser URLs and delegate common `gh` shortcuts."""

    def __init__(self, context: GitHubRepoContext, *, cwd: Path | None = None) -> None:
        self.context = context
        self.cwd = cwd or Path.cwd()

    @classmethod
    def from_repo(
        cls,
        *,
        cwd: str | Path | None = None,
        remote: str = "origin",
    ) -> GitHubShortcutService:
        probe_cwd = Path(cwd or Path.cwd()).resolve()
        repo_root = Path(_run_git(probe_cwd, "rev-parse", "--show-toplevel")).resolve()
        remote_url = _run_git(repo_root, "remote", "get-url", remote)
        branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
        head_sha = _run_git(repo_root, "rev-parse", "HEAD")
        host, owner, repo = _parse_remote_url(remote_url)
        context = GitHubRepoContext(
            repo_root=repo_root,
            remote_name=remote,
            host=host,
            owner=owner,
            repo=repo,
            branch=branch,
            head_sha=head_sha,
        )
        return cls(context, cwd=probe_cwd)

    def resolve_repo_path(self, path: str | Path) -> str:
        """Resolve a local or repo-relative path into a repo-relative POSIX path."""
        raw_path = Path(path)
        candidates = []
        if raw_path.is_absolute():
            candidates.append(raw_path.resolve(strict=False))
        else:
            candidates.append((self.cwd / raw_path).resolve(strict=False))
            candidates.append((self.context.repo_root / raw_path).resolve(strict=False))

        for candidate in candidates:
            if candidate.is_relative_to(self.context.repo_root):
                return candidate.relative_to(self.context.repo_root).as_posix()

        raise GitHubShortcutError(f"{path} does not resolve inside {self.context.repo_root}.")

    def dev_url(self, path: str | Path | None = None) -> str:
        base = self.context.dev_base_url()
        if path is None:
            return base
        repo_path = self.resolve_repo_path(path)
        return (
            f"{base}/blob/{_quote_ref(self.context.current_ref)}/{_quote_path(repo_path)}"
        )

    def permalink_url(
        self,
        path: str | Path | None = None,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        if path is None:
            return f"{self.context.web_base_url}/tree/{_quote_ref(self.context.head_sha)}"

        repo_path = self.resolve_repo_path(path)
        url = (
            f"{self.context.web_base_url}/blob/{_quote_ref(self.context.head_sha)}/"
            f"{_quote_path(repo_path)}"
        )
        anchor = self._line_anchor(start_line, end_line)
        if anchor:
            url = f"{url}{anchor}"
        return url

    def blame_url(self, path: str | Path, *, ref: str | None = None) -> str:
        repo_path = self.resolve_repo_path(path)
        chosen_ref = ref or self.context.current_ref
        return (
            f"{self.context.web_base_url}/blame/{_quote_ref(chosen_ref)}/"
            f"{_quote_path(repo_path)}"
        )

    def history_url(self, path: str | Path, *, ref: str | None = None) -> str:
        repo_path = self.resolve_repo_path(path)
        chosen_ref = ref or self.context.current_ref
        return (
            f"{self.context.web_base_url}/commits/{_quote_ref(chosen_ref)}/"
            f"{_quote_path(repo_path)}"
        )

    def search_url(
        self,
        query: str,
        *,
        path: str | None = None,
        language: str | None = None,
        symbol: str | None = None,
        repo_scoped: bool = True,
    ) -> str:
        terms: list[str] = []
        cleaned_query = query.strip()
        if cleaned_query:
            terms.append(cleaned_query)
        if repo_scoped:
            terms.append(f"repo:{self.context.name_with_owner}")
        if path:
            terms.append(f"path:{path}")
        if language:
            terms.append(f"lang:{language}")
        if symbol:
            terms.append(f"symbol:{symbol}")
        if not terms:
            raise GitHubShortcutError("Provide a query or at least one qualifier to build the search URL.")

        q = " ".join(terms)
        return f"https://{self.context.host}/search?q={quote_plus(q)}&type=code"

    def diff_url(
        self,
        *,
        pr_number: int | None = None,
        commit_sha: str | None = None,
        format_name: str = "patch",
    ) -> str:
        if (pr_number is None) == (commit_sha is None):
            raise GitHubShortcutError("Choose exactly one target: `--pr` or `--commit`.")
        if format_name not in {"patch", "diff"}:
            raise GitHubShortcutError("Format must be either `patch` or `diff`.")

        if pr_number is not None:
            return f"{self.context.web_base_url}/pull/{pr_number}.{format_name}"
        return f"{self.context.web_base_url}/commit/{commit_sha}.{format_name}"

    def review_url(self, pr_number: int) -> str:
        return f"{self.context.web_base_url}/pull/{pr_number}/commits"

    @staticmethod
    def open_url(url: str) -> bool:
        return webbrowser.open(url, new=2)

    @staticmethod
    def _line_anchor(start_line: int | None, end_line: int | None) -> str:
        if start_line is None:
            return ""
        if end_line is None or start_line == end_line:
            return f"#L{start_line}"
        return f"#L{start_line}-L{end_line}"


def run_gh(args: list[str], *, cwd: str | Path | None = None) -> None:
    """Run a GitHub CLI command with a friendly failure mode."""
    if shutil.which("gh") is None:
        raise GitHubShortcutError("`gh` is required for this shortcut but is not installed.")

    try:
        completed = subprocess.run(
            ["gh", *args],
            check=False,
            cwd=str(cwd) if cwd is not None else None,
        )
    except FileNotFoundError as err:
        raise GitHubShortcutError("`gh` is required for this shortcut but is not installed.") from err

    if completed.returncode != 0:
        raise GitHubShortcutError(f"`gh {' '.join(args)}` exited with status {completed.returncode}.")
