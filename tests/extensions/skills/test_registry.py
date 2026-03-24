from pathlib import Path

from cortex.extensions.skills.registry import SkillRegistry


def test_extensions_registry_falls_back_to_bundled_skills() -> None:
    registry = SkillRegistry(base_dir=Path("/tmp/cortex-missing-skills")).load()

    manifest = registry.get("hours-saved")
    assert manifest is not None
    assert manifest.category == "metrics"
    assert manifest.primary_trigger == "/hours_saved"
    assert manifest._raw_frontmatter["Hours_Saved"] == 1000000

    ops_manifest = registry.get("ops-kpi")
    assert ops_manifest is not None
    assert ops_manifest.primary_trigger == "/ops_kpi"
    assert ops_manifest._raw_frontmatter["Cost_Saved_EUR"] == 42000
    assert ops_manifest._raw_frontmatter["Tasks_Automated"] == 144
