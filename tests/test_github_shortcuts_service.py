from __future__ import annotations

from pathlib import Path

import pytest

from cortex.services.github_shortcuts import (
    GitHubRepoContext,
    GitHubShortcutError,
    GitHubShortcutService,
    parse_line_spec,
)


def _make_service(tmp_path: Path, *, host: str = "github.com") -> GitHubShortcutService:
    repo_root = tmp_path / "repo"
    file_path = repo_root / "cortex" / "cli" / "github_cmds.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("pass\n", encoding="utf-8")

    context = GitHubRepoContext(
        repo_root=repo_root,
        remote_name="origin",
        host=host,
        owner="acme",
        repo="cortex",
        branch="main",
        head_sha="deadbeefcafebabe",
    )
    return GitHubShortcutService(context, cwd=repo_root / "cortex")


def test_parse_line_spec_accepts_single_line() -> None:
    assert parse_line_spec("10") == (10, 10)


def test_parse_line_spec_accepts_range() -> None:
    assert parse_line_spec("10-25") == (10, 25)


def test_parse_line_spec_rejects_invalid_range() -> None:
    with pytest.raises(GitHubShortcutError):
        parse_line_spec("25-10")


def test_dev_url_targets_github_dev(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    url = service.dev_url("cli/github_cmds.py")

    assert url == "https://github.dev/acme/cortex/blob/main/cortex/cli/github_cmds.py"


def test_dev_url_rejects_non_github_dot_com(tmp_path: Path) -> None:
    service = _make_service(tmp_path, host="github.enterprise.local")

    with pytest.raises(GitHubShortcutError):
        service.dev_url()


def test_permalink_url_pins_head_sha_and_lines(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    url = service.permalink_url("cli/github_cmds.py", start_line=10, end_line=25)

    assert (
        url
        == "https://github.com/acme/cortex/blob/deadbeefcafebabe/cortex/cli/github_cmds.py#L10-L25"
    )


def test_search_url_builds_repo_scoped_query(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    url = service.search_url(
        "store_fact",
        path="cortex/engine",
        language="python",
        symbol="CortexEngine",
    )

    assert "repo%3Aacme%2Fcortex" in url
    assert "path%3Acortex%2Fengine" in url
    assert "lang%3Apython" in url
    assert "symbol%3ACortexEngine" in url
    assert "store_fact" in url


def test_diff_url_supports_pr_and_commit_exports(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    assert service.diff_url(pr_number=42, format_name="patch") == (
        "https://github.com/acme/cortex/pull/42.patch"
    )
    assert service.diff_url(commit_sha="abcdef", format_name="diff") == (
        "https://github.com/acme/cortex/commit/abcdef.diff"
    )


def test_history_and_blame_urls_use_current_branch_by_default(tmp_path: Path) -> None:
    service = _make_service(tmp_path)

    assert service.blame_url("cli/github_cmds.py") == (
        "https://github.com/acme/cortex/blame/main/cortex/cli/github_cmds.py"
    )
    assert service.history_url("cli/github_cmds.py") == (
        "https://github.com/acme/cortex/commits/main/cortex/cli/github_cmds.py"
    )
