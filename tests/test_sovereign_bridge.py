import importlib
import sys
import types

import pytest

from cortex.extensions.sovereign.bridge import SovereignBridge


def _make_skill(tmp_path, name: str, entrypoint: str = "main.py", body: str = ""):
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (skill_dir / entrypoint).write_text(
        body or "def main(*args, **kwargs):\n    return kwargs\n", encoding="utf-8"
    )
    return skill_dir


@pytest.fixture(autouse=True)
def _cleanup_bridge_modules():
    sys.modules.pop("helper", None)
    yield
    sys.modules.pop("helper", None)


def test_discover_and_load_registers_skill_dirs_with_skill_md(tmp_path):
    _make_skill(tmp_path, "demo-skill")
    ignored = tmp_path / "no-manifest"
    ignored.mkdir()
    (ignored / "main.py").write_text("def main():\n    return 'ignored'\n", encoding="utf-8")

    bridge = SovereignBridge(skills_root=tmp_path)

    assert bridge.list_skills() == ["demo-skill"]


def test_execute_missing_skill_raises_clear_import_error(tmp_path):
    bridge = SovereignBridge(skills_root=tmp_path)

    with pytest.raises(ImportError, match="missing-skill"):
        bridge.execute("missing-skill")


def test_execute_uses_filesystem_entrypoint_not_stdlib_antigravity_namespace(tmp_path, monkeypatch):
    _make_skill(
        tmp_path,
        "demo-skill",
        body="def main(*args, **kwargs):\n    return {'args': list(args), 'kwargs': kwargs}\n",
    )

    def _fail_import_module(*args, **kwargs):
        raise AssertionError("stdlib antigravity namespace should not be used")

    monkeypatch.setattr(importlib, "import_module", _fail_import_module)

    bridge = SovereignBridge(skills_root=tmp_path)
    result = bridge.execute("demo-skill", 1, mode="test")

    assert result == {"args": [1], "kwargs": {"mode": "test"}}


def test_execute_supports_sortu_style_engine_entrypoint(tmp_path):
    _make_skill(
        tmp_path,
        "Sortu",
        entrypoint="sortu_engine.py",
        body="from helper import VALUE\n\ndef run():\n    return VALUE\n",
    )
    (tmp_path / "Sortu" / "helper.py").write_text("VALUE = 7\n", encoding="utf-8")

    bridge = SovereignBridge(skills_root=tmp_path)

    assert bridge.execute("Sortu") == 7


def test_execute_isolates_local_modules_between_skills(tmp_path):
    _make_skill(
        tmp_path, "Alpha", body="from helper import VALUE\n\ndef main():\n    return VALUE\n"
    )
    (tmp_path / "Alpha" / "helper.py").write_text("VALUE = 'alpha'\n", encoding="utf-8")

    _make_skill(
        tmp_path, "Beta", body="from helper import VALUE\n\ndef main():\n    return VALUE\n"
    )
    (tmp_path / "Beta" / "helper.py").write_text("VALUE = 'beta'\n", encoding="utf-8")

    bridge = SovereignBridge(skills_root=tmp_path)

    assert bridge.execute("Alpha") == "alpha"
    assert bridge.execute("Beta") == "beta"


def test_execute_supports_runtime_local_imports(tmp_path):
    _make_skill(
        tmp_path, "Gamma", body="def main():\n    import helper\n\n    return helper.VALUE\n"
    )
    (tmp_path / "Gamma" / "helper.py").write_text("VALUE = 11\n", encoding="utf-8")

    bridge = SovereignBridge(skills_root=tmp_path)

    assert bridge.execute("Gamma") == 11


def test_module_origin_avoids_lazy_module_side_effects(tmp_path):
    module = types.ModuleType("lazy_module")

    def _fail_getattr(name: str):
        raise AssertionError(f"unexpected lazy attribute access: {name}")

    module.__getattr__ = _fail_getattr

    assert SovereignBridge._module_origin(module) is None

    module.__file__ = str(tmp_path / "skill.py")

    assert SovereignBridge._module_origin(module) == (tmp_path / "skill.py").resolve()
