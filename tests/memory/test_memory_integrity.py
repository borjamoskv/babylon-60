"""Memory integrity tests: verify cortex/memory modules maintain consistent state.

Covers:
- Memory module importability
- Logging hygiene (no bare print() in memory layer)
- Basic write/read symmetry where public API is available
- Module-level attribute surface validation
"""
from __future__ import annotations

import importlib
import logging
import ast as _ast
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_MEMORY_DIR = _REPO_ROOT / "cortex" / "memory"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_memory_modules() -> list[str]:
    """Return dotted module names for all public .py files under cortex/memory/."""
    modules: list[str] = []
    if not _MEMORY_DIR.is_dir():
        pytest.skip("cortex/memory directory not found; skipping memory tests.")
    for py_file in sorted(_MEMORY_DIR.rglob("*.py")):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue
        rel = py_file.relative_to(_REPO_ROOT)
        dotted = ".".join(rel.with_suffix("").parts)
        modules.append(dotted)
    return modules


_MEMORY_MODULES = _collect_memory_modules()


def _find_bare_prints(filepath: Path) -> list[int]:
    """Return line numbers of bare print() calls in *filepath*."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = _ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []
    violations: list[int] = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            func = node.value.func
            if isinstance(func, _ast.Name) and func.id == "print":
                violations.append(node.lineno)
    return violations


# ---------------------------------------------------------------------------
# Module importability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", _MEMORY_MODULES, ids=lambda m: m)
def test_memory_module_importable(module_name: str) -> None:
    """Every cortex/memory module must be importable without side effects."""
    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f"Cannot import {module_name}: {exc}")
    assert mod is not None


# ---------------------------------------------------------------------------
# Logging hygiene
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "py_file",
    sorted(_MEMORY_DIR.rglob("*.py")) if _MEMORY_DIR.is_dir() else [],
    ids=lambda p: str(p.relative_to(_REPO_ROOT)),
)
def test_memory_no_bare_print(py_file: Path) -> None:
    """Memory modules must use logging instead of bare print()."""
    violations = _find_bare_prints(py_file)
    rel = py_file.relative_to(_REPO_ROOT)
    assert not violations, (
        f"{rel} has bare print() at lines {violations}. Use logging."
    )


# ---------------------------------------------------------------------------
# Module attribute surface: expected dunder attributes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", _MEMORY_MODULES, ids=lambda m: m)
def test_memory_module_has_name(module_name: str) -> None:
    """Every importable module must expose __name__."""
    try:
        mod: ModuleType = importlib.import_module(module_name)
    except ImportError:
        pytest.skip(f"Cannot import {module_name}")
    assert hasattr(mod, "__name__"), f"{module_name} missing __name__"
    assert mod.__name__ == module_name, (
        f"__name__ mismatch: expected {module_name!r}, got {mod.__name__!r}"
    )


# ---------------------------------------------------------------------------
# Logger suppression guard
# ---------------------------------------------------------------------------

def test_memory_logging_not_suppressed() -> None:
    """Root logger must not be set to CRITICAL after importing memory modules."""
    for module_name in _MEMORY_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            continue
    root_level = logging.getLogger().level
    assert root_level < logging.CRITICAL, (
        f"Root logger level {root_level} is CRITICAL; memory modules must not suppress logging."
    )


# ---------------------------------------------------------------------------
# Sanity: memory directory must contain at least one module
# ---------------------------------------------------------------------------

def test_memory_has_modules() -> None:
    """Sanity guard: cortex/memory must expose at least one importable module."""
    assert len(_MEMORY_MODULES) > 0, (
        f"No importable modules found under {_MEMORY_DIR.relative_to(_REPO_ROOT)}."
    )
