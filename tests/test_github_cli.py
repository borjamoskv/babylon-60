from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import cortex.cli.github_cmds as github_cli
from cortex.cli import cli


def test_github_group_is_registered_on_root_cli() -> None:
    assert "github" in cli.commands


def test_github_help_lists_subcommands() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["github", "--help"])

    assert result.exit_code == 0
    assert "dev" in result.output
    assert "agent-demo" in result.output
    assert "permalink" in result.output
    assert "search" in result.output
    assert "diff-url" in result.output
    assert "review" in result.output
    assert "blame" in result.output
    assert "history" in result.output
    assert "pr" in result.output
    assert "repo" in result.output
    assert "sync" in result.output
    assert "status" in result.output


def test_github_permalink_prints_commit_pinned_url(monkeypatch) -> None:
    class _FakeService:
        def permalink_url(
            self,
            path: str | None = None,
            *,
            start_line: int | None = None,
            end_line: int | None = None,
        ) -> str:
            assert path == "cortex/cli/github_cmds.py"
            assert start_line == 10
            assert end_line == 25
            return "https://github.com/acme/cortex/blob/deadbeef/cortex/cli/github_cmds.py#L10-L25"

    monkeypatch.setattr(github_cli, "_get_shortcut_service", lambda remote: _FakeService())

    result = CliRunner().invoke(
        cli,
        ["github", "permalink", "cortex/cli/github_cmds.py", "--lines", "10-25"],
    )

    assert result.exit_code == 0
    assert "https://github.com/acme/cortex/blob/deadbeef/" in result.output
    assert "#L10-L25" in result.output


def test_github_pr_view_delegates_to_gh(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def _fake_repo_cwd(remote: str) -> Path:
        calls["remote"] = remote
        return Path("/tmp/repo")

    def _fake_run_gh_shortcut(args: list[str], *, cwd: Path | None = None) -> None:
        calls["args"] = args
        calls["cwd"] = cwd

    monkeypatch.setattr(github_cli, "_repo_cwd", _fake_repo_cwd)
    monkeypatch.setattr(github_cli, "_run_gh_shortcut", _fake_run_gh_shortcut)

    result = CliRunner().invoke(cli, ["github", "pr", "view", "123", "--web"])

    assert result.exit_code == 0
    assert calls == {
        "remote": "origin",
        "args": ["pr", "view", "123", "--web"],
        "cwd": Path("/tmp/repo"),
    }


def test_github_agent_demo_delegates_to_runner(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_async(coro):
        captured["awaitable"] = coro
        coro.close()
        return {"op": "status", "result": {"status": "ok"}}

    def _fake_emit(payload: dict[str, object]) -> None:
        captured["payload"] = payload

    monkeypatch.setattr(github_cli, "_run_async", _fake_run_async)
    monkeypatch.setattr(github_cli, "_emit_json_result", _fake_emit)

    result = CliRunner().invoke(cli, ["github", "agent-demo", "--op", "status"])

    assert result.exit_code == 0
    assert captured["payload"] == {"op": "status", "result": {"status": "ok"}}
    assert "awaitable" in captured
