from pathlib import Path

from cortex.extensions.agents.apis_omega import ApisOmegaAgent
from cortex.extensions.llm._presets import default_presets_path


def test_apis_omega_default_presets_path_is_canonical() -> None:
    agent = ApisOmegaAgent()

    assert agent.presets_path == default_presets_path()
    assert agent.presets_path == Path("config/llm_presets.json").resolve()
