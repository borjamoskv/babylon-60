from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

from cortex.cli import cli
from cortex.cli import skills_cmds as skills_cli_module


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_skills_kpi_outputs_hours_saved(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["skills", "kpi", "hours-saved"])

    assert result.exit_code == 0
    assert result.output.strip() == "Hours_Saved: 1000000"


def test_skills_kpi_outputs_ops_bundle_as_json(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["skills", "kpi", "ops-kpi", "--json-output"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["skill_name"] == "ops-kpi"
    assert payload["trigger"] == "ops_kpi"
    assert payload["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
        "Tasks_Automated": 144,
    }


def test_skills_list_filters_kpi_skills(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["skills", "list", "--category", "metrics", "--kpi-only"])

    assert result.exit_code == 0
    assert "hours-saved" in result.output
    assert "ops-kpi" in result.output
    assert "cortex-persist" not in result.output


def test_skills_kpi_rejects_non_kpi_skill(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["skills", "kpi", "cortex-persist"])

    assert result.exit_code != 0
    assert "does not expose canonical KPIs" in result.output


class _FakeCLIEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.history_rows: list[dict[str, Any]] = []

    def store_sync(
        self,
        *,
        project: str,
        content: str,
        fact_type: str,
        tags: list[str],
        source: str,
        meta: dict[str, Any],
    ) -> int:
        self.calls.append(
            {
                "project": project,
                "content": content,
                "fact_type": fact_type,
                "tags": tags,
                "source": source,
                "meta": meta,
            }
        )
        return 314

    async def history(self, *, project: str) -> list[dict[str, Any]]:
        self.calls.append({"history_project": project})
        return self.history_rows


def test_skills_snapshot_persists_fact(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _FakeCLIEngine()
    monkeypatch.setattr(skills_cli_module, "get_engine", lambda db: engine)
    monkeypatch.setattr(skills_cli_module, "close_engine_sync", lambda _engine: None)

    result = runner.invoke(
        cli,
        [
            "skills",
            "snapshot",
            "ops-kpi",
            "--project",
            "metrics",
            "--tag",
            "daily",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["skill_name"] == "ops-kpi"
    assert payload["project"] == "metrics"
    assert payload["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
        "Tasks_Automated": 144,
    }
    assert len(engine.calls) == 1
    latest = engine.calls[0]
    assert latest["project"] == "metrics"
    assert "Canonical KPI snapshot for skill 'ops-kpi'" in latest["content"]
    assert latest["source"] == "cli:skills"
    assert "daily" in latest["tags"]
    assert latest["meta"]["skill_name"] == "ops-kpi"


def test_skills_history_lists_snapshots(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _FakeCLIEngine()
    engine.history_rows = [
        {
            "id": 12,
            "project": "metrics",
            "fact_type": "knowledge",
            "source": "cli:skills",
            "content": "Canonical KPI snapshot for skill 'ops-kpi' at 2026-03-24T11:00:00Z",
            "tags": ["kpi", "skill", "ops-kpi", "daily"],
            "created_at": "2026-03-24T11:00:01Z",
            "meta": {
                "skill_name": "ops-kpi",
                "captured_at": "2026-03-24T11:00:00Z",
                "metrics": {
                    "Hours_Saved": 1000000,
                    "Cost_Saved_EUR": 42000,
                    "Tasks_Automated": 144,
                },
            },
        }
    ]
    monkeypatch.setattr(skills_cli_module, "get_engine", lambda db: engine)
    monkeypatch.setattr(skills_cli_module, "close_engine_sync", lambda _engine: None)

    result = runner.invoke(
        cli,
        ["skills", "history", "ops-kpi", "--project", "metrics", "--json-output"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 1
    assert payload[0]["fact_id"] == 12
    assert payload[0]["metrics"]["Cost_Saved_EUR"] == 42000
