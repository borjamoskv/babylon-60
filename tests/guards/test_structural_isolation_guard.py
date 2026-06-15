# [C5-REAL] Exergy-Maximized
import pytest
from cortex.guards.structural_isolation_guard import (
    StructuralIsolationGuard,
    StructuralIsolationViolation,
)


def test_structural_isolation_guard_valid_c5():
    guard = StructuralIsolationGuard()
    # Safe C5-REAL payload
    valid_content = """
    # [C5-REAL]
    This is verified output with zero simulation.
    Check out the repo at [cortex](file:///Users/borjafernandezangulo/30_CORTEX).
    """
    # Should not raise anything
    guard.check(valid_content)


def test_structural_isolation_guard_valid_c4():
    guard = StructuralIsolationGuard()
    # Safe C4-SIM payload
    valid_content = """
    # [C4-SIM]
    This is a simulation representing simulated capital and yields.
    """
    guard.check(valid_content)


def test_structural_isolation_guard_missing_reality_declaration():
    guard = StructuralIsolationGuard()
    content = "Just plain text with no reality level declared."
    with pytest.raises(StructuralIsolationViolation, match="Missing reality level declaration"):
        guard.check(content)


def test_structural_isolation_guard_contradictory_declaration():
    guard = StructuralIsolationGuard()
    content = "Contains both C5-REAL and C4-SIM markers."
    with pytest.raises(StructuralIsolationViolation, match="Contradictory state"):
        guard.check(content)


def test_structural_isolation_guard_simulated_proof_in_c5():
    guard = StructuralIsolationGuard()
    content = """
    # [C5-REAL]
    We have simulated capital of $10,000.
    """
    with pytest.raises(StructuralIsolationViolation, match="contains simulated proof keyword"):
        guard.check(content)


def test_structural_isolation_guard_protected_path_violation():
    guard = StructuralIsolationGuard()
    content = """
    # [C5-REAL]
    Accessing database from /System/Volumes/Data/private/var/db/
    """
    with pytest.raises(StructuralIsolationViolation, match="Attempted access to protected path"):
        guard.check(content)


def test_structural_isolation_guard_markdown_link_with_backticks():
    guard = StructuralIsolationGuard()
    content = """
    # [C5-REAL]
    Please refer to [`utils.py`](file:///path/to/utils.py)
    """
    with pytest.raises(StructuralIsolationViolation, match="Markdown links must not surround link text with backticks"):
        guard.check(content)
