from __future__ import annotations

import pytest

from cortex.guards.dependency_guard import DependencyScanError, scan_file


def test_scan_file_reports_oracle_dependency(tmp_path):
    target = tmp_path / "oracle_call.py"
    target.write_text(
        "import subprocess\n"
        "subprocess.run(['openai', 'prompt'], check=False)\n",
        encoding="utf-8",
    )

    violations = scan_file(target)

    assert len(violations) == 1
    assert violations[0].binary == "openai"


def test_scan_file_fails_closed_on_invalid_encoding(tmp_path):
    target = tmp_path / "invalid_encoding.py"
    target.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(DependencyScanError, match="failed to read"):
        scan_file(target)


def test_scan_file_fails_closed_on_syntax_error(tmp_path):
    target = tmp_path / "invalid_syntax.py"
    target.write_text(
        "import subprocess\n"
        "def broken(:\n"
        "    subprocess.run(['openai'])\n",
        encoding="utf-8",
    )

    with pytest.raises(DependencyScanError, match="failed to parse"):
        scan_file(target)
