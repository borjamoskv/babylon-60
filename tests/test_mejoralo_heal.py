from __future__ import annotations

import subprocess

from cortex.extensions.mejoralo.heal import (
    _apply_generation_results,
    _build_delta_test_command,
    _run_delta_testing,
    _select_healing_targets,
)
from cortex.extensions.mejoralo.models import DimensionResult, ScanResult


class _DummyConsole:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


class _DummyEngine:
    def __init__(self) -> None:
        self.scars: list[tuple[str, str, str]] = []

    def record_scar(self, project: str, file_path: str, reason: str) -> None:
        self.scars.append((project, file_path, reason))


def _scan_result_with_findings(*findings: str) -> ScanResult:
    return ScanResult(
        project="mejoralo",
        stack="python",
        score=50,
        dimensions=[
            DimensionResult(name="Complexity", score=50, weight="high", findings=list(findings))
        ],
        dead_code=False,
    )


def test_build_delta_test_command_prefers_direct_test_file(tmp_path) -> None:
    console = _DummyConsole()
    test_file = tmp_path / "tests" / "test_scan.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

    command = _build_delta_test_command("cortex/extensions/mejoralo/scan.py", tmp_path, console)

    assert command[1:3] == ["-m", "pytest"]
    assert str(test_file) in command
    assert any("Delta-Testing" in message for message in console.messages)


def test_select_healing_targets_uses_topological_order_and_level_budget(monkeypatch) -> None:
    scan_result = _scan_result_with_findings(
        "alpha.py:10 -> issue A",
        "beta.py:20 -> issue B",
    )

    monkeypatch.setattr(
        "cortex.extensions.mejoralo.heal.sort_by_topological_order",
        lambda file_issues, path: [
            ("beta.py", file_issues["beta.py"]),
            ("alpha.py", file_issues["alpha.py"]),
        ],
    )
    monkeypatch.setattr("cortex.extensions.mejoralo.heal._get_files_per_iteration", lambda level: 1)

    targets = _select_healing_targets(scan_result, "/tmp/worktree", level=2)

    assert targets == [("beta.py", ["(Complexity) beta.py:20 -> issue B"])]


def test_run_delta_testing_rolls_back_and_records_regression(tmp_path, monkeypatch) -> None:
    console = _DummyConsole()
    engine = _DummyEngine()
    abs_path = tmp_path / "target.py"
    original_code = "print('original')\n"
    abs_path.write_text("print('new')\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=kwargs.get("args", []),
            returncode=1,
            stdout="boom",
            stderr="trace",
        )

    monkeypatch.setattr("cortex.extensions.mejoralo.heal.subprocess.run", fake_run)

    ok = _run_delta_testing(
        top_file_rel="misc/target.py",
        path=tmp_path,
        original_code=original_code,
        abs_path=abs_path,
        console=console,
        engine=engine,
        project="mejoralo",
        level=1,
    )

    assert ok is False
    assert abs_path.read_text(encoding="utf-8") == original_code
    assert engine.scars == [("mejoralo", "misc/target.py", "boom\ntrace")]


def test_apply_generation_results_skips_tainted_and_tracks_success(monkeypatch) -> None:
    console = _DummyConsole()
    healed_files: set[str] = set()

    monkeypatch.setattr(
        "cortex.extensions.mejoralo.heal.is_file_tainted",
        lambda file_path, project, engine: file_path == "tainted.py",
    )
    applied: list[str] = []
    monkeypatch.setattr(
        "cortex.extensions.mejoralo.heal._apply_and_verify",
        lambda top_file_rel, *args, **kwargs: applied.append(top_file_rel) or True,
    )

    ok = _apply_generation_results(
        targets=[("tainted.py", ["issue"]), ("healthy.py", ["issue"])],
        generation_results=["patched tainted", "patched healthy"],
        path=".",
        level=1,
        iteration=1,
        console=console,
        current_score=50,
        healed_files=healed_files,
        engine=None,
        project="mejoralo",
    )

    assert ok is True
    assert applied == ["healthy.py"]
    assert healed_files == {"healthy.py"}


def test_run_delta_testing_marks_l3_taint_on_regression(tmp_path, monkeypatch) -> None:
    console = _DummyConsole()
    engine = _DummyEngine()
    abs_path = tmp_path / "target.py"
    abs_path.write_text("print('new')\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="boom", stderr="trace")

    tainted: list[tuple[str, str]] = []
    monkeypatch.setattr("cortex.extensions.mejoralo.heal.subprocess.run", fake_run)
    monkeypatch.setattr(
        "cortex.extensions.mejoralo.heal.mark_file_tainted",
        lambda file_path, project, engine_obj: tainted.append((file_path, project)),
    )

    ok = _run_delta_testing(
        top_file_rel="misc/target.py",
        path=tmp_path,
        original_code="print('original')\n",
        abs_path=abs_path,
        console=console,
        engine=engine,
        project="mejoralo",
        level=3,
    )

    assert ok is False
    assert tainted == [("misc/target.py", "mejoralo")]
