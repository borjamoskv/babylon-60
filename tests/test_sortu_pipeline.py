"""Test the 10-step Sovereign Object Runtime Universal (SORTU) pipeline."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Prefer the tracked Sortu implementation so CI and local runs exercise the repo code.
LOCAL_SORTU_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "sortu"
if LOCAL_SORTU_SCRIPTS.exists() and str(LOCAL_SORTU_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LOCAL_SORTU_SCRIPTS))

# Fallback to the host Antigravity install only when the tracked copy is unavailable.
SORTU_SKILL_DIR = Path.home() / ".gemini/antigravity/skills/Sortu"
if (
    not LOCAL_SORTU_SCRIPTS.exists()
    and SORTU_SKILL_DIR.exists()
    and str(SORTU_SKILL_DIR) not in sys.path
):
    sys.path.insert(0, str(SORTU_SKILL_DIR))

try:
    from sortu_engine import SortuEngine
except ImportError:
    pass


@pytest.fixture
def mock_sortu_skill(tmp_path: Path) -> Path:
    """Fixture that generates a structurally valid Tripartite package."""
    skill_dir = tmp_path / "DummySkill"
    skill_dir.mkdir()

    # 1. SKILL.md
    (skill_dir / "SKILL.md").write_text(
        "---\nname: DummySkill\nversion: 1.0.0\nclassification: TEST\ndanger_level: LOW\n---\n"
        "# Dummy Skill",
        encoding="utf-8",
    )

    # 2. schema.json
    (skill_dir / "schema.json").write_text(
        '{"$schema": "...", "title":"dummy", "type":"object", "required":[], "properties":{}}',
        encoding="utf-8",
    )

    # 3. verify_dummy.py
    (skill_dir / "verify_dummy.py").write_text(
        "#!/usr/bin/env python3\nprint('PASS')\n",
        encoding="utf-8",
    )

    return skill_dir


@pytest.mark.asyncio
async def test_sortu_pipeline_e2e_valid(mock_sortu_skill: Path, tmp_path: Path) -> None:
    """Test standard SORTU e2e execution."""
    if not (LOCAL_SORTU_SCRIPTS.exists() or SORTU_SKILL_DIR.exists()):
        pytest.skip("Sortu not present in host environment.")

    # Mocking GraphStore to avoid touching real DB

    mock_graph_store = AsyncMock()

    engine = SortuEngine(skills_root=tmp_path, graph_store=mock_graph_store)

    # Needs a dummy invocation_log to pass yield check
    log = [{"hours_saved": 10.0, "chain_depth": 1, "latency_ms": 100.0, "success": True}]

    record = await engine.forge(mock_sortu_skill, intent="Testing", invocation_log=log)

    assert record.state.value == "ACTIVE"
    assert record.biopsy is not None
    assert record.biopsy.net_exergy > 0
    assert record.graph_entities_created == 1  # 1 Node (the skill itself) is linked in test


@pytest.mark.asyncio
async def test_sortu_pipeline_abort(tmp_path: Path) -> None:
    """Test pipeline aborts cleanly."""
    if not (LOCAL_SORTU_SCRIPTS.exists() or SORTU_SKILL_DIR.exists()):
        pytest.skip("Sortu not present in host environment.")

    skill_dir = tmp_path / "InvalidSkill"
    skill_dir.mkdir(parents=True)

    engine = SortuEngine(skills_root=tmp_path)
    record = await engine.forge(skill_dir)

    assert record.state.value == "ABORTED"
    assert record.abort_reason.value == "MISSING_TRIPARTITE"
