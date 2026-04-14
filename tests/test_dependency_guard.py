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


def test_scan_file_preserves_critical_violation_when_duplicate_warning_exists(tmp_path, monkeypatch):
    from cortex.guards import dependency_guard as module

    target = tmp_path / "oracle_call.py"
    target.write_text("import subprocess\nsubprocess.run(['openai'])\n", encoding="utf-8")

    monkeypatch.setattr(module.analysis, "has_exec_import", lambda source: True)
    monkeypatch.setattr(module.analysis, "has_sovereign_fallback", lambda source: False)
    monkeypatch.setattr(module.analysis, "has_exec_calls", lambda tree: True)
    monkeypatch.setattr(
        module.analysis,
        "find_violations",
        lambda tree: [(2, "openai", "string_literal"), (2, "openai", "subprocess.run")],
    )
    monkeypatch.setattr(module.analysis, "find_oracle_string_literals", lambda tree, exec_calls: [])

    violations = scan_file(target)

    assert len(violations) == 1
    assert violations[0].binary == "openai"
    assert violations[0].call_type == "subprocess.run"
    assert violations[0].has_fallback is False


def test_main_exits_nonzero_on_warning_only(tmp_path, monkeypatch, capsys):
    from cortex.guards import dependency_guard as module
    from cortex.guards.models import DependencyViolation

    target = tmp_path / "dummy.py"
    target.write_text("print('noop')\n", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "scan_file",
        lambda path: [
            DependencyViolation(
                file=str(path),
                line=1,
                binary="openai",
                call_type="string_literal",
                has_fallback=True,
            )
        ],
    )
    monkeypatch.setattr(module.sys, "argv", ["dependency_guard.py", str(target)])

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == 1
