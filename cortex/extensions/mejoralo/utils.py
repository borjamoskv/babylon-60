"""Utilities for MEJORAlo engine."""

import subprocess
from pathlib import Path
from typing import Any, Optional

from .constants import STACK_MARKERS

__all__ = [
    "detect_stack",
    "get_build_cmd",
    "get_lint_cmd",
    "get_test_cmd",
    "run_quiet",
]


def detect_stack(path: str | Path) -> str:
    """Detect project stack from marker files."""
    p = check_safe_path(path)
    for stack, marker in STACK_MARKERS.items():
        if (p / marker).exists():
            return stack
    return "unknown"


def get_build_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "run", "build"],
        "python": ["python", "-m", "py_compile", "."],
        "swift": ["swift", "build"],
    }
    return cmds.get(stack)


def get_test_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npm", "test"],
        "python": ["python", "-m", "pytest", "--tb=no", "-q"],
        "swift": ["swift", "test"],
    }
    return cmds.get(stack)


def get_lint_cmd(stack: str) -> Optional[list[str]]:
    cmds = {
        "node": ["npx", "eslint", "."],
        "python": ["python", "-m", "ruff", "check", "."],
    }
    return cmds.get(stack)


def run_quiet(cmd: list[str], cwd: str) -> dict[str, Any]:
    """Run a command quietly, capturing output."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            timeout=120,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
        }


try:
    from cortex.cortex_rs import (
        check_safe_path as rs_check_safe_path,
    )
    _HAS_RS_SAFETY = True
except ImportError:
    _HAS_RS_SAFETY = False


def check_safe_path(path: str | Path) -> Path:
    """Ensure the path is safe to use and resolve it.

    Uses Rust-native validation for O(1) performance
    and kernel-level boundary checks.
    """
    p = Path(path).expanduser()
    resolved = p.resolve()

    # 1. Rust-native boundary enforcement (Axiom Ω0)
    if _HAS_RS_SAFETY:
        cwd = Path.cwd().resolve()
        if not rs_check_safe_path(str(cwd), str(resolved)):
            # Exception: allow /tmp for scratch space
            if not str(resolved).startswith("/tmp"):
                raise ValueError(
                    "Security: Blocked traversal"
                    f" attempt (Rust Guard) to {resolved}"
                )
    else:
        # Python Fallback
        cwd = Path.cwd().resolve()
        if not str(resolved).startswith(str(cwd)):
            if not str(resolved).startswith("/tmp"):
                raise ValueError(
                    "Security: Blocked traversal"
                    f" attempt (Legacy Guard)"
                    f" to {resolved}"
                )

    return resolved
