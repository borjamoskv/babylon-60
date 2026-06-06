# [C5-REAL] Exergy-Maximized
"""Mirror Audit — Cyclomatic Complexity Checker for CORTEX.

Implements the TODO at cortex-core/mirror_audit.py line 59:
    # TODO: Add cyclomatic complexity check in v6.5

Purpose:
  AST-based cyclomatic complexity measurement that scans all Python
  source files under the `cortex/` directory and reports functions
  that exceed configured thresholds.

Thresholds (v6.5):
  complexity <= 10  → PASS
  11 <= complexity <= 20 → WARN
  complexity > 20  → FAIL

Output per function:
  file_path | function_name | complexity | status

Usage::

    from cortex.audit.mirror_audit import run_complexity_audit, ComplexityStatus
    report = run_complexity_audit(root="cortex")
    for result in report.results:
        if result.status != ComplexityStatus.PASS:
            print(result)
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

__all__ = [
    "ComplexityStatus",
    "ComplexityResult",
    "ComplexityReport",
    "measure_cyclomatic_complexity",
    "scan_file",
    "run_complexity_audit",
]

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

WARN_THRESHOLD: int = 10
FAIL_THRESHOLD: int = 20


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ComplexityStatus(str, Enum):
    """Result tier for a single function's cyclomatic complexity."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

    @classmethod
    def from_score(cls, score: int) -> ComplexityStatus:
        """Derive status from a raw complexity score."""
        if score > FAIL_THRESHOLD:
            return cls.FAIL
        if score > WARN_THRESHOLD:
            return cls.WARN
        return cls.PASS


@dataclass(frozen=True)
class ComplexityResult:
    """Per-function complexity measurement."""

    file_path: str
    function_name: str
    lineno: int
    complexity: int
    status: ComplexityStatus

    def __str__(self) -> str:
        return (
            f"{self.file_path}:{self.lineno} | {self.function_name} "
            f"| complexity={self.complexity} | {self.status.value.upper()}"
        )


@dataclass
class ComplexityReport:
    """Aggregated result from a full directory scan."""

    root: str
    results: list[ComplexityResult] = field(default_factory=list)

    # ----- convenience accessors -------------------------------------------

    @property
    def passes(self) -> list[ComplexityResult]:
        """Functions within acceptable complexity bounds."""
        return [r for r in self.results if r.status == ComplexityStatus.PASS]

    @property
    def warnings(self) -> list[ComplexityResult]:
        """Functions that exceed the warn threshold."""
        return [r for r in self.results if r.status == ComplexityStatus.WARN]

    @property
    def failures(self) -> list[ComplexityResult]:
        """Functions that exceed the fail threshold."""
        return [r for r in self.results if r.status == ComplexityStatus.FAIL]

    @property
    def has_failures(self) -> bool:
        """True when at least one function exceeds the FAIL threshold."""
        return bool(self.failures)

    def summary(self) -> dict[str, int]:
        """Return a count summary keyed by status."""
        return {
            "total": len(self.results),
            "pass": len(self.passes),
            "warn": len(self.warnings),
            "fail": len(self.failures),
        }


# ---------------------------------------------------------------------------
# Core AST-based complexity measurement
# ---------------------------------------------------------------------------

# Branch-contributing node types per McCabe (1976).
_BRANCH_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.Assert,
    ast.comprehension,
    ast.BoolOp,
    ast.IfExp,  # ternary
    ast.Match,  # Python 3.10+
)


def measure_cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the McCabe cyclomatic complexity for a function/method node.

    Complexity = 1 + (number of branch-creating nodes in the AST subtree).
    For BoolOp (and/or), each additional operand adds 1 branch.
    """
    complexity = 1  # base path
    for child in ast.walk(node):
        if isinstance(child, ast.BoolOp):
            # `a and b and c` has 2 operators → adds len(values) - 1
            complexity += len(child.values) - 1
        elif isinstance(child, _BRANCH_NODES):
            complexity += 1
    return complexity


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def scan_file(file_path: Path) -> Iterator[ComplexityResult]:
    """Parse a single Python source file and yield ComplexityResult per function.

    Skips files that cannot be parsed (logs a warning).
    Handles nested functions independently (each measured on its own subtree).
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        logger.warning("[mirror_audit] Syntax error in %s: %s", file_path, exc)
        return
    except OSError as exc:
        logger.warning("[mirror_audit] Cannot read %s: %s", file_path, exc)
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            score = measure_cyclomatic_complexity(node)
            status = ComplexityStatus.from_score(score)
            result = ComplexityResult(
                file_path=str(file_path),
                function_name=node.name,
                lineno=node.lineno,
                complexity=score,
                status=status,
            )
            if status == ComplexityStatus.WARN:
                logger.warning("[mirror_audit] WARN %s", result)
            elif status == ComplexityStatus.FAIL:
                logger.error("[mirror_audit] FAIL %s", result)
            yield result


# ---------------------------------------------------------------------------
# Directory-level orchestrator
# ---------------------------------------------------------------------------


def run_complexity_audit(
    root: str | Path = "cortex",
    *,
    warn_threshold: int = WARN_THRESHOLD,
    fail_threshold: int = FAIL_THRESHOLD,
    exclude_dirs: frozenset[str] | None = None,
) -> ComplexityReport:
    """Scan all .py files under *root* and return a ComplexityReport.

    Args:
        root: Root directory to scan (default: ``"cortex"``).
        warn_threshold: Complexity above which a WARN is issued (default: 10).
        fail_threshold: Complexity above which a FAIL is issued (default: 20).
        exclude_dirs: Directory names to skip (e.g. ``{"migrations", "__pycache__"}``).

    Returns:
        A :class:`ComplexityReport` with all measurement results.
    """
    # Allow callers to override thresholds without monkey-patching globals.
    global WARN_THRESHOLD, FAIL_THRESHOLD  # noqa: PLW0603
    _orig_warn, _orig_fail = WARN_THRESHOLD, FAIL_THRESHOLD
    WARN_THRESHOLD = warn_threshold
    FAIL_THRESHOLD = fail_threshold

    _excluded: frozenset[str] = exclude_dirs or frozenset(
        {"__pycache__", ".git", ".venv", "migrations", "node_modules"}
    )
    root_path = Path(root)
    report = ComplexityReport(root=str(root_path.resolve()))

    logger.info("[mirror_audit] Scanning %s (warn>%d, fail>%d)", root_path, warn_threshold, fail_threshold)

    for py_file in sorted(root_path.rglob("*.py")):
        # Skip excluded directories
        if any(part in _excluded for part in py_file.parts):
            continue
        for result in scan_file(py_file):
            report.results.append(result)

    # Restore thresholds so concurrent callers aren't surprised.
    WARN_THRESHOLD = _orig_warn
    FAIL_THRESHOLD = _orig_fail

    summary = report.summary()
    logger.info(
        "[mirror_audit] Scan complete: %d functions scanned, "
        "%d PASS / %d WARN / %d FAIL",
        summary["total"],
        summary["pass"],
        summary["warn"],
        summary["fail"],
    )
    return report


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _root = sys.argv[1] if len(sys.argv) > 1 else "cortex"
    _report = run_complexity_audit(root=_root)
    for _r in sorted(_report.results, key=lambda x: x.complexity, reverse=True):
        if _r.status != ComplexityStatus.PASS:
            print(_r)  # noqa: T201 — intentional CLI output
    _s = _report.summary()
    print(f"\nSummary: {_s['total']} functions | {_s['pass']} PASS | {_s['warn']} WARN | {_s['fail']} FAIL")  # noqa: T201
    sys.exit(1 if _report.has_failures else 0)
