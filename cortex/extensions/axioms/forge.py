# SPDX-License-Identifier: Apache-2.0
"""Axiom Forge — Executable Philosophy Engine v1.0.

Transforms CORTEX axioms from aspirational text into deterministic
verification functions. Each axiom becomes a callable that returns
a ForgeVerdict: PASS, FAIL, or SKIP (when preconditions are unmet).

Usage:
    from cortex.extensions.axioms.forge import AxiomForge
    forge = AxiomForge("/path/to/cortex/repo")
    results = forge.verify_all()
    forge.report(results)

AX-033: The truth does not emerge from the model; it is imposed
through topology — forced collapse, guards as failure boundaries.
"""

from __future__ import annotations

import ast
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from cortex.extensions.axioms.registry import AXIOM_REGISTRY, Axiom


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class ForgeResult:
    """Result of verifying a single axiom against the codebase."""

    axiom_id: str
    axiom_name: str
    verdict: Verdict
    message: str
    violations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_failure(self) -> bool:
        return self.verdict == Verdict.FAIL


# Type alias for verification functions
VerifyFn = Callable[["AxiomForge"], ForgeResult]

# Global registry of verification functions
_VERIFIERS: dict[str, VerifyFn] = {}


def verifies(axiom_id: str) -> Callable[[VerifyFn], VerifyFn]:
    """Decorator to register a function as the verifier for an axiom."""

    def decorator(fn: VerifyFn) -> VerifyFn:
        _VERIFIERS[axiom_id] = fn
        return fn

    return decorator


class AxiomForge:
    """The Forge. Turns axioms into tests, violations into errors.

    Initialize with the root of the CORTEX repository.
    Call verify_all() to run all registered verifiers.
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.cortex_root = self.repo_root / "cortex"
        if not self.cortex_root.is_dir():
            raise FileNotFoundError(f"cortex/ not found in {self.repo_root}")

    def verify(self, axiom_id: str) -> ForgeResult:
        """Run a single axiom verifier."""
        if axiom_id not in _VERIFIERS:
            ax = AXIOM_REGISTRY.get(axiom_id)
            name = ax.name if ax else "Unknown"
            return ForgeResult(
                axiom_id=axiom_id,
                axiom_name=name,
                verdict=Verdict.SKIP,
                message=f"No verifier registered for {axiom_id}",
            )
        return _VERIFIERS[axiom_id](self)

    def verify_all(self) -> list[ForgeResult]:
        """Run all registered verifiers."""
        results: list[ForgeResult] = []
        for axiom_id in sorted(AXIOM_REGISTRY.keys()):
            results.append(self.verify(axiom_id))
        return results

    def verify_enforced(self) -> list[ForgeResult]:
        """Run only verifiers for axioms that have registered enforcement."""
        results: list[ForgeResult] = []
        for axiom_id in sorted(_VERIFIERS.keys()):
            results.append(self.verify(axiom_id))
        return results

    def python_files(self, exclude_tests: bool = False) -> list[Path]:
        """List all Python files in cortex/."""
        files = list(self.cortex_root.rglob("*.py"))
        if exclude_tests:
            files = [f for f in files if "/test" not in str(f)]
        return [f for f in files if "__pycache__" not in str(f)]

    def file_lines(self, path: Path) -> list[str]:
        """Read a file and return its lines."""
        return path.read_text(encoding="utf-8", errors="replace").splitlines()

    def is_git_repo(self) -> bool:
        """Check if repo_root is inside a git repository."""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def git_untracked(self, path: str) -> list[str]:
        """Return untracked files under a given path."""
        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", path],
                cwd=str(self.repo_root),
                check=True,
                capture_output=True,
                text=True,
            )
            return [f for f in result.stdout.strip().splitlines() if f]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @staticmethod
    def report(results: list[ForgeResult]) -> str:
        """Generate a human-readable report of forge results."""
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("  AXIOM FORGE — Executable Philosophy Report")
        lines.append("=" * 70)

        passed = sum(1 for r in results if r.verdict == Verdict.PASS)
        failed = sum(1 for r in results if r.verdict == Verdict.FAIL)
        skipped = sum(1 for r in results if r.verdict == Verdict.SKIP)

        for r in results:
            icon = {"PASS": "✅", "FAIL": "🔴", "SKIP": "⬜"}[r.verdict.value]
            lines.append(f"  {icon} {r.axiom_id} [{r.axiom_name}]: {r.verdict.value}")
            if r.verdict == Verdict.FAIL:
                lines.append(f"     └─ {r.message}")
                for v in r.violations[:5]:
                    lines.append(f"        • {v}")
                if len(r.violations) > 5:
                    lines.append(f"        ... and {len(r.violations) - 5} more")

        lines.append("")
        lines.append(f"  PASSED: {passed}  |  FAILED: {failed}  |  SKIPPED: {skipped}")
        lines.append(f"  ENFORCEMENT RATE: {passed}/{passed + failed} "
                      f"({round(passed / max(passed + failed, 1) * 100)}%)")
        lines.append("=" * 70)
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VERIFIERS — Each function is the executable form of an axiom
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@verifies("AX-011")
def _verify_entropy_death(forge: AxiomForge) -> ForgeResult:
    """AX-011: Entropy Death — ≤300 LOC/file. Dead code = death."""
    MAX_LOC = 300
    violations: list[str] = []

    for path in forge.python_files(exclude_tests=True):
        lines = forge.file_lines(path)
        # Count non-empty, non-comment lines
        loc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
        if loc > MAX_LOC:
            rel = path.relative_to(forge.repo_root)
            violations.append(f"{rel}: {loc} LOC (max {MAX_LOC})")

    if violations:
        return ForgeResult(
            axiom_id="AX-011",
            axiom_name="Entropy Death",
            verdict=Verdict.FAIL,
            message=f"{len(violations)} files exceed {MAX_LOC} LOC limit",
            violations=tuple(violations),
        )

    return ForgeResult(
        axiom_id="AX-011",
        axiom_name="Entropy Death",
        verdict=Verdict.PASS,
        message=f"All {len(forge.python_files(exclude_tests=True))} files within LOC limit",
    )


@verifies("AX-013")
def _verify_async_native(forge: AxiomForge) -> ForgeResult:
    """AX-013: Async Native — time.sleep() PROHIBITED in async code."""
    violations: list[str] = []

    for path in forge.python_files(exclude_tests=True):
        lines = forge.file_lines(path)
        in_async = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("async def "):
                in_async = True
            elif stripped.startswith("def ") and not stripped.startswith("async def"):
                in_async = False
            elif in_async and "time.sleep(" in stripped:
                rel = path.relative_to(forge.repo_root)
                violations.append(f"{rel}:{i} — time.sleep() inside async context")

    if violations:
        return ForgeResult(
            axiom_id="AX-013",
            axiom_name="Async Native",
            verdict=Verdict.FAIL,
            message=f"{len(violations)} time.sleep() calls found in async code",
            violations=tuple(violations),
        )

    return ForgeResult(
        axiom_id="AX-013",
        axiom_name="Async Native",
        verdict=Verdict.PASS,
        message="No time.sleep() found in async code paths",
    )


@verifies("AX-017")
def _verify_ledger_integrity(forge: AxiomForge) -> ForgeResult:
    """AX-017: Ledger Integrity — SHA-256 hash chain must exist."""
    ledger_dir = forge.cortex_root / "ledger"
    if not ledger_dir.is_dir():
        return ForgeResult(
            axiom_id="AX-017",
            axiom_name="Ledger Integrity",
            verdict=Verdict.FAIL,
            message="cortex/ledger/ directory does not exist",
        )

    # Verify hash chain implementation exists
    has_sha256 = False
    has_merkle = False
    for path in ledger_dir.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="replace")
        if "sha256" in content.lower() or "hashlib" in content:
            has_sha256 = True
        if "merkle" in content.lower():
            has_merkle = True

    violations = []
    if not has_sha256:
        violations.append("No SHA-256 hash chain implementation found in cortex/ledger/")
    if not has_merkle:
        violations.append("No Merkle tree implementation found in cortex/ledger/")

    if violations:
        return ForgeResult(
            axiom_id="AX-017",
            axiom_name="Ledger Integrity",
            verdict=Verdict.FAIL,
            message="Missing cryptographic integrity components",
            violations=tuple(violations),
        )

    return ForgeResult(
        axiom_id="AX-017",
        axiom_name="Ledger Integrity",
        verdict=Verdict.PASS,
        message="SHA-256 hash chain and Merkle tree present in ledger module",
    )


@verifies("AX-010")
def _verify_zero_trust(forge: AxiomForge) -> ForgeResult:
    """AX-010: Zero Trust — classify_content() BEFORE every INSERT."""
    storage_dir = forge.cortex_root / "storage"
    if not storage_dir.is_dir():
        return ForgeResult(
            axiom_id="AX-010",
            axiom_name="Zero Trust",
            verdict=Verdict.SKIP,
            message="cortex/storage/ directory not found",
        )

    # Check that storage modules reference classification before writes
    violations: list[str] = []
    for path in storage_dir.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Files that perform INSERT must reference classify/classification/privacy
        if "INSERT" in content or "insert" in content.lower():
            has_guard = any(
                term in content.lower()
                for term in ["classify", "classification", "privacy", "guard", "taint"]
            )
            if not has_guard:
                rel = path.relative_to(forge.repo_root)
                violations.append(f"{rel}: INSERT without classification guard")

    if violations:
        return ForgeResult(
            axiom_id="AX-010",
            axiom_name="Zero Trust",
            verdict=Verdict.FAIL,
            message=f"{len(violations)} storage files INSERT without classification",
            violations=tuple(violations),
        )

    return ForgeResult(
        axiom_id="AX-010",
        axiom_name="Zero Trust",
        verdict=Verdict.PASS,
        message="All storage INSERT paths reference classification guards",
    )


@verifies("AX-012")
def _verify_type_safety(forge: AxiomForge) -> ForgeResult:
    """AX-012: Type Safety — from __future__ import annotations in all files."""
    violations: list[str] = []

    for path in forge.python_files(exclude_tests=True):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Skip empty files and __init__.py with only imports
        lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        if len(lines) < 3:
            continue

        if "from __future__ import annotations" not in content:
            rel = path.relative_to(forge.repo_root)
            violations.append(f"{rel}: missing 'from __future__ import annotations'")

    if violations:
        return ForgeResult(
            axiom_id="AX-012",
            axiom_name="Type Safety",
            verdict=Verdict.FAIL,
            message=f"{len(violations)} files missing future annotations import",
            violations=tuple(violations),
        )

    return ForgeResult(
        axiom_id="AX-012",
        axiom_name="Type Safety",
        verdict=Verdict.PASS,
        message="All files use 'from __future__ import annotations'",
    )


@verifies("AX-019")
def _verify_persist_with_decay(forge: AxiomForge) -> ForgeResult:
    """AX-019: Persist With Decay — TTL policy must be defined for all fact types."""
    try:
        from cortex.extensions.axioms.ttl import FACT_TTL
    except ImportError:
        return ForgeResult(
            axiom_id="AX-019",
            axiom_name="Persist With Decay",
            verdict=Verdict.FAIL,
            message="Cannot import TTL policy module",
        )

    # Verify minimum required fact types have TTL definitions
    required_types = {"axiom", "decision", "error", "ghost", "knowledge", "bridge"}
    missing = required_types - set(FACT_TTL.keys())

    if missing:
        return ForgeResult(
            axiom_id="AX-019",
            axiom_name="Persist With Decay",
            verdict=Verdict.FAIL,
            message=f"TTL policy missing for: {missing}",
            violations=tuple(f"Missing TTL for fact type: {t}" for t in sorted(missing)),
        )

    # Verify axioms are immortal
    if FACT_TTL.get("axiom") is not None:
        return ForgeResult(
            axiom_id="AX-019",
            axiom_name="Persist With Decay",
            verdict=Verdict.FAIL,
            message="Axioms must have TTL=None (immortal). Current TTL is not None.",
        )

    return ForgeResult(
        axiom_id="AX-019",
        axiom_name="Persist With Decay",
        verdict=Verdict.PASS,
        message=f"TTL defined for {len(FACT_TTL)} fact types. Axioms are immortal.",
    )
