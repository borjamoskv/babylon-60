from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "repo_health_changed.py"


def _load_repo_health_module():
    spec = importlib.util.spec_from_file_location("repo_health_changed", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_banner_separator_is_not_treated_as_merge_marker(tmp_path) -> None:
    module = _load_repo_health_module()
    sample = tmp_path / "banner.py"
    sample.write_text(
        '"""\nSection Title\n=================================\n"""\nvalue = 1\n',
        encoding="utf-8",
    )

    assert module._text_contains_conflict_markers(sample) == []


def test_explicit_file_scan_fails_on_real_merge_markers(tmp_path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text(
        "<<<<<<< HEAD\nvalue = 1\n=======\nvalue = 2\n>>>>>>> origin/main\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(broken)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "[repo-health] FAIL" in result.stdout
    assert "merge conflict markers" in result.stdout
