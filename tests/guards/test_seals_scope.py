from __future__ import annotations

from pathlib import Path

from cortex.guards import seals


def test_scope_python_files_repo_scope_collects_cortex_sources(tmp_path: Path) -> None:
    (tmp_path / "cortex" / "nested").mkdir(parents=True)
    (tmp_path / "cortex" / "tests_support").mkdir(parents=True)
    (tmp_path / "cortex" / "nested" / "alpha.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "cortex" / "nested" / "beta.pyc").write_text("", encoding="utf-8")
    (tmp_path / "cortex" / "tests_support" / "helper.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_alpha.py").write_text("assert True\n", encoding="utf-8")

    result = seals._scope_python_files(root_dir=tmp_path, scope="repo")

    assert result == [tmp_path / "cortex" / "nested" / "alpha.py"]


def test_scope_python_files_changed_scope_prefers_changed_manifest(tmp_path: Path) -> None:
    (tmp_path / "cortex" / "engine").mkdir(parents=True)
    (tmp_path / "cortex" / "engine" / "guard_pipeline.py").write_text(
        "from __future__ import annotations\n",
        encoding="utf-8",
    )
    (tmp_path / "cortex" / "engine" / "notes.txt").write_text("n/a\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("docs\n", encoding="utf-8")
    (tmp_path / ".changed_files").write_text(
        "README.md\ncortex/engine/guard_pipeline.py\ncortex/engine/notes.txt\n",
        encoding="utf-8",
    )

    result = seals._scope_python_files(root_dir=tmp_path, scope="changed")

    assert result == [tmp_path / "cortex" / "engine" / "guard_pipeline.py"]
