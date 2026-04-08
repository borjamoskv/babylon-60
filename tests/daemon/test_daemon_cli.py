from __future__ import annotations

import json

from click.testing import CliRunner

from cortex.extensions.daemon import cli as daemon_cli


def test_config_command_json_reports_paths_and_current_config(
    monkeypatch,
    tmp_path,
) -> None:
    config_path = tmp_path / "daemon_config.json"
    config_path.write_text(json.dumps({"autopoiesis_target_score": 97}))
    example_path = tmp_path / "daemon_config.example.json"
    example_path.write_text(json.dumps({"autopoiesis_focus": "entropy"}))

    monkeypatch.setattr(daemon_cli, "CONFIG_FILE", config_path)
    monkeypatch.setattr(daemon_cli, "_daemon_example_path", lambda: example_path)

    result = CliRunner().invoke(daemon_cli.cli, ["config", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["config_exists"] is True
    assert payload["example_exists"] is True
    assert payload["current_config"]["autopoiesis_target_score"] == 97
    assert any(
        item["key"] == "autopoiesis_enable_manifestation" for item in payload["autopoiesis_keys"]
    )


def test_config_command_example_prints_example_file(monkeypatch, tmp_path) -> None:
    example_path = tmp_path / "daemon_config.example.json"
    example_body = '{\n  "autopoiesis_enable_healing": true\n}\n'
    example_path.write_text(example_body)

    monkeypatch.setattr(daemon_cli, "_daemon_example_path", lambda: example_path)

    result = CliRunner().invoke(daemon_cli.cli, ["config", "--example"])

    assert result.exit_code == 0
    assert result.output == example_body


def test_config_command_validate_fails_for_invalid_types(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "daemon_config.json"
    config_path.write_text(json.dumps({"autopoiesis_target_score": "high"}))
    example_path = tmp_path / "daemon_config.example.json"
    example_path.write_text("{}")

    monkeypatch.setattr(daemon_cli, "CONFIG_FILE", config_path)
    monkeypatch.setattr(daemon_cli, "_daemon_example_path", lambda: example_path)

    result = CliRunner().invoke(daemon_cli.cli, ["config", "--validate"])

    assert result.exit_code == 1
    assert "autopoiesis_target_score" in result.output
    assert "must be an integer" in result.output


def test_start_fails_fast_when_daemon_config_is_invalid(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "daemon_config.json"
    config_path.write_text(json.dumps({"sites": "https://example.com"}))

    created: dict[str, bool] = {"called": False}

    class _StubDaemon:
        def __init__(self, *args, **kwargs) -> None:
            created["called"] = True

        def run(self, interval: int) -> None:
            created["called"] = True

    monkeypatch.setattr(daemon_cli, "CONFIG_FILE", config_path)
    monkeypatch.setattr(daemon_cli, "MoskvDaemon", _StubDaemon)

    result = CliRunner().invoke(daemon_cli.cli, ["start"])

    assert result.exit_code == 1
    assert created["called"] is False
    assert "Invalid daemon config" in result.output
