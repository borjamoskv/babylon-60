from __future__ import annotations

from click.testing import CliRunner

import cortex.cli.agent_cmds as agent_cli
from cortex.cli import cli


def test_agent_group_is_registered_on_root_cli() -> None:
    assert "agent" in cli.commands


def test_agent_help_lists_github_builtin_command() -> None:
    result = CliRunner().invoke(cli, ["agent", "--help"])

    assert result.exit_code == 0
    assert "github" in result.output
    assert "github-repl" in result.output
    assert "run" in result.output
    assert "validate" in result.output


def test_agent_github_delegates_to_demo_runner(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_async(coro):
        captured["awaitable"] = coro
        coro.close()
        return {"ok": True, "op": "status", "result": {"status": "ok"}}

    def _fake_emit(payload: dict[str, object]) -> None:
        captured["payload"] = payload

    monkeypatch.setattr(agent_cli, "_run_async", _fake_run_async)
    monkeypatch.setattr(agent_cli, "_emit_json_result", _fake_emit)

    result = CliRunner().invoke(cli, ["agent", "github", "--op", "status"])

    assert result.exit_code == 0
    assert captured["payload"] == {"ok": True, "op": "status", "result": {"status": "ok"}}
    assert "awaitable" in captured


def test_parse_github_repl_line_accepts_key_value_syntax() -> None:
    payload = agent_cli._parse_github_repl_line(
        "permalink path=cortex/cli/github_cmds.py lines=10-25"
    )

    assert payload == {
        "op": "permalink",
        "remote": "origin",
        "path": "cortex/cli/github_cmds.py",
        "lines": "10-25",
    }


def test_parse_github_repl_line_accepts_json_syntax() -> None:
    payload = agent_cli._parse_github_repl_line('{"op":"status","remote":"origin"}')

    assert payload == {"op": "status", "remote": "origin"}
