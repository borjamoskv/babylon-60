from __future__ import annotations

import importlib

from cortex.extensions.evolution.agents import AgentDomain


def _write_skill(tmp_path, dirname: str, name: str) -> None:
    skill_dir = tmp_path / dirname
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\nversion: 1.0.0\n---\n",
        encoding="utf-8",
    )


def test_skill_registry_get_resolves_legacy_alias(monkeypatch, tmp_path) -> None:
    _write_skill(tmp_path, "CORTEX-Orchestra-Omega", "CORTEX-Orchestra-Omega")
    monkeypatch.setenv("CORTEX_SKILLS_DIR", str(tmp_path))

    import cortex.core.paths as paths_module
    import cortex.extensions.skills.registry as registry_module

    importlib.reload(paths_module)
    registry_module = importlib.reload(registry_module)

    registry = registry_module.SkillRegistry().load(force_reload=True)
    manifest = registry.get("keter-omega")

    assert manifest is not None
    assert manifest.name == "CORTEX-Orchestra-Omega"


def test_skill_bridge_consolidates_communication_and_synergy(monkeypatch, tmp_path) -> None:
    _write_skill(tmp_path, "Comms-Hub-Omega", "Comms-Hub-Omega")
    _write_skill(tmp_path, "Cognitive-Crystallizer-Omega", "Cognitive-Crystallizer-Omega")
    monkeypatch.setenv("CORTEX_SKILLS_DIR", str(tmp_path))

    import cortex.core.paths as paths_module
    import cortex.extensions.evolution.skill_bridge as skill_bridge_module

    importlib.reload(paths_module)
    skill_bridge_module = importlib.reload(skill_bridge_module)

    assert skill_bridge_module.get_skill_for_domain(AgentDomain.COMMUNICATION) == "comms-hub-omega"
    assert skill_bridge_module.get_skill_for_domain(AgentDomain.SYNERGY) == "singularity-nexus"
    assert skill_bridge_module.get_domain_for_skill("Comms-Hub-Omega") is AgentDomain.COMMUNICATION
    assert (
        skill_bridge_module.get_domain_for_skill("Cognitive-Crystallizer-Omega")
        is AgentDomain.SYNERGY
    )

    summary = skill_bridge_module.get_skill_summary()
    assert summary["mapping"]["COMMUNICATION"]["resolved_skill"] == "Comms-Hub-Omega"
    assert summary["mapping"]["COMMUNICATION"]["installed"] is True
    assert summary["mapping"]["SYNERGY"]["resolved_skill"] == "Cognitive-Crystallizer-Omega"
    assert summary["mapping"]["SYNERGY"]["installed"] is True
