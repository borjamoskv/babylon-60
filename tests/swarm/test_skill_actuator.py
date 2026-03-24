from pathlib import Path

import pytest

from cortex.swarm.actuators.skill import SkillActuator
from cortex.swarm.discovery import SkillMetadata
from cortex.swarm.manager import SwarmManager


@pytest.mark.asyncio
async def test_hours_saved_skill_returns_canonical_kpi() -> None:
    manager = SwarmManager()
    manager.registry.scan()

    response = await manager.dispatch("hours-saved", "report canonical hours saved")

    assert response["status"] == "success"
    assert response["content"] == "Hours_Saved: 1000000"
    assert response["metadata"]["skill_name"] == "hours-saved"
    assert response["metadata"]["metric_name"] == "Hours_Saved"
    assert response["metadata"]["metric_value"] == 1000000
    assert response["metadata"]["hours_saved"] == 1000000
    assert response["metadata"]["metrics"] == {"Hours_Saved": 1000000}
    assert response["metadata"]["mode"] == "canonical_kpi"


@pytest.mark.asyncio
async def test_skill_actuator_returns_multiple_canonical_metrics() -> None:
    skill = SkillMetadata(
        {
            "name": "ops-kpi",
            "description": "Bundled operational metrics.",
            "version": "1.0.0",
            "category": "metrics",
            "trigger": "ops_kpi",
            "Hours_Saved": 1000000,
            "Cost_Saved_EUR": 42000,
        },
        Path("/tmp/ops-kpi/SKILL.md"),
    )

    response = await SkillActuator(skill).execute("report", {})

    assert response["status"] == "success"
    assert response["content"] == "Hours_Saved: 1000000\nCost_Saved_EUR: 42000"
    assert response["metadata"]["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
    }
    assert "metric_name" not in response["metadata"]
    assert "hours_saved" not in response["metadata"]
    assert response["metadata"]["mode"] == "canonical_kpi"


@pytest.mark.asyncio
async def test_ops_kpi_skill_dispatch_returns_bundled_metrics() -> None:
    manager = SwarmManager()
    manager.registry.scan()

    response = await manager.dispatch("ops-kpi", "report bundled ops kpis")

    assert response["status"] == "success"
    assert response["content"] == (
        "Hours_Saved: 1000000\n"
        "Cost_Saved_EUR: 42000\n"
        "Tasks_Automated: 144"
    )
    assert response["metadata"]["skill_name"] == "ops-kpi"
    assert response["metadata"]["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
        "Tasks_Automated": 144,
    }
    assert "metric_name" not in response["metadata"]
