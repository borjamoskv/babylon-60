from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_workspace.py"


def _load_reconcile_workspace_module():
    spec = importlib.util.spec_from_file_location("reconcile_workspace", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def test_discover_workspace_residue_only_flags_noncanonical_top_level_dirs(tmp_path: Path) -> None:
    module = _load_reconcile_workspace_module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    _run_git(repo_root, "init")

    tracked_file = repo_root / "cortex" / "__init__.py"
    tracked_file.parent.mkdir(parents=True)
    tracked_file.write_text("", encoding="utf-8")
    _run_git(repo_root, "add", "cortex/__init__.py")

    clone_dir = repo_root / "X-COPY-ZONES"
    clone_dir.mkdir()
    (clone_dir / "package.json").write_text('{"name":"clone"}', encoding="utf-8")

    generated_dir = repo_root / "artifacts"
    generated_dir.mkdir()
    (generated_dir / "trace.txt").write_text("local-only", encoding="utf-8")

    nested_untracked = repo_root / "cortex" / "extensions" / "bpo"
    nested_untracked.mkdir(parents=True)
    (nested_untracked / "mod.py").write_text("value = 1\n", encoding="utf-8")

    entries = module.discover_workspace_residue(repo_root)
    names = [entry.name for entry in entries]

    assert names == ["X-COPY-ZONES", "artifacts"]

    clone_entry = entries[0]
    assert clone_entry.classification == "cloned-subproject"
    assert clone_entry.markers == ("package.json",)

    generated_entry = entries[1]
    assert generated_entry.classification == "generated-residue"


def test_write_local_exclude_is_idempotent(tmp_path: Path) -> None:
    module = _load_reconcile_workspace_module()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    _run_git(repo_root, "init")

    exclude_path = repo_root / ".git" / "info" / "exclude"
    exclude_path.write_text("# base\n", encoding="utf-8")

    entries = [
        module.ResidueEntry(
            name="X-COPY-ZONES",
            path=repo_root / "X-COPY-ZONES",
            size_bytes=0,
            classification="cloned-subproject",
            markers=("package.json",),
            destination_hint="move to sibling repo or quarantine",
        ),
        module.ResidueEntry(
            name="artifacts",
            path=repo_root / "artifacts",
            size_bytes=0,
            classification="generated-residue",
            markers=(),
            destination_hint="keep local-only",
        ),
    ]

    added_count, additions = module.write_local_exclude(repo_root, entries)
    assert added_count == 2
    assert additions == ["X-COPY-ZONES/", "artifacts/"]

    second_count, second_additions = module.write_local_exclude(repo_root, entries)
    assert second_count == 0
    assert second_additions == []

    content = exclude_path.read_text(encoding="utf-8")
    assert "X-COPY-ZONES/" in content
    assert "artifacts/" in content
