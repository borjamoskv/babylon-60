from pathlib import Path

from cortex.swarm.discovery import SkillRegistry


def test_swarm_registry_falls_back_to_bundled_skills() -> None:
    registry = SkillRegistry(base_path=Path("/tmp/cortex-missing-skills"))

    skills = registry.scan()

    manifest = skills.get("hours-saved")
    assert manifest is not None
    assert manifest.category == "metrics"
    assert manifest.trigger == "hours_saved"
    assert manifest["Hours_Saved"] == 1000000

    ops_manifest = skills.get("ops-kpi")
    assert ops_manifest is not None
    assert ops_manifest.category == "metrics"
    assert ops_manifest.trigger == "ops_kpi"
    assert ops_manifest["Cost_Saved_EUR"] == 42000
    assert ops_manifest["Tasks_Automated"] == 144
