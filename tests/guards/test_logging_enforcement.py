import ast
import os
from pathlib import Path
import pytest

# Target directories to scan for bare print() calls
TARGET_DIRS = [
    "cortex/engine",
    "cortex/memory",
    "cortex/guards",
    "cortex/core",
    "cortex/database",
    "cortex/agents",
]


def find_bare_print_calls(directory: str) -> list[str]:
    violations = []
    root_path = Path(directory)

    if not root_path.exists():
        return []

    for py_file in root_path.rglob("*.py"):
        # Skip cli modules as per rules
        if "cli/" in str(py_file) or "tests/" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))

            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    violations.append(f"{py_file}:{node.lineno}")
        except (OSError, SyntaxError):
            continue

    return violations


@pytest.mark.parametrize("directory", TARGET_DIRS)
def test_no_bare_print_in_core_modules(directory):
    """Verify that no bare print() calls remain in production core modules."""
    violations = find_bare_print_calls(directory)
    assert not violations, f"Bare print() found in {directory}: {violations}"
