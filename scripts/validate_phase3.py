#!/usr/bin/env python3
"""Fast validation gate for phase-3 causal-chain work.

This is intentionally narrow:
- Ruff on the phase-3 implementation/test surfaces
- ``py_compile`` on the same Python files
- Targeted pytest nodes covering phase-3 behavior

Usage:
    python3 scripts/validate_phase3.py
"""

from __future__ import annotations

import py_compile
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
PYTHON: Final[str] = str(REPO_ROOT / ".venv" / "bin" / "python")
RUFF: Final[str] = str(REPO_ROOT / ".venv" / "bin" / "ruff")
PYTEST: Final[str] = str(REPO_ROOT / ".venv" / "bin" / "pytest")

PHASE3_FILES: Final[tuple[str, ...]] = (
    "cortex/engine/query_mixin.py",
    "cortex/engine/__init__.py",
    "cortex/engine/sync_mixin.py",
    "cortex/cli/memory_cmds.py",
    "cortex/mcp/server.py",
    "cortex/mcp/core_tools.py",
    "tests/test_parent_decision_id.py",
)

PHASE3_TESTS: Final[tuple[str, ...]] = (
    "tests/test_parent_decision_id.py::TestEngineAPI",
    "tests/test_parent_decision_id.py::TestCLI",
    "tests/test_parent_decision_id.py::TestMCP",
    "tests/test_parent_decision_id.py::TestCausalChainTraversal",
)


@dataclass(slots=True)
class StepResult:
    name: str
    ok: bool
    duration_ms: float
    detail: str


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _format_detail(result: subprocess.CompletedProcess[str]) -> str:
    for stream in (result.stdout, result.stderr):
        text = stream.strip()
        if text:
            return text.splitlines()[-1][:240]
    return "ok"


def check_ruff() -> StepResult:
    started = time.monotonic()
    result = _run([RUFF, "check", *PHASE3_FILES])
    return StepResult(
        name="ruff",
        ok=result.returncode == 0,
        duration_ms=(time.monotonic() - started) * 1000,
        detail="clean" if result.returncode == 0 else _format_detail(result),
    )


def check_py_compile() -> StepResult:
    started = time.monotonic()
    errors: list[str] = []
    for relative_path in PHASE3_FILES:
        path = REPO_ROOT / relative_path
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{relative_path}: {exc.msg}")

    return StepResult(
        name="py_compile",
        ok=not errors,
        duration_ms=(time.monotonic() - started) * 1000,
        detail="compiled" if not errors else errors[0][:240],
    )


def check_pytest() -> StepResult:
    started = time.monotonic()
    result = _run([PYTEST, "-q", "--tb=short", *PHASE3_TESTS])
    lines = [line for line in result.stdout.strip().splitlines() if line]
    summary = lines[-1] if lines else _format_detail(result)
    return StepResult(
        name="pytest",
        ok=result.returncode == 0,
        duration_ms=(time.monotonic() - started) * 1000,
        detail=summary,
    )


def main() -> int:
    missing = [tool for tool in (PYTHON, RUFF, PYTEST) if not Path(tool).exists()]
    if missing:
        print("phase3-fast: missing tooling in .venv")
        for tool in missing:
            print(f"- {tool}")
        return 2

    results = [check_ruff(), check_py_compile(), check_pytest()]
    failed = False

    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name} ({result.duration_ms:.0f} ms) :: {result.detail}")
        failed = failed or not result.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
