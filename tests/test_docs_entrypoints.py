from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_readme_and_package_metadata_point_to_external_docs() -> None:
    readme = _read("README.md")
    pyproject = _read("pyproject.toml")

    assert "https://cortexpersist.com/docs" in readme
    assert 'Documentation = "https://cortexpersist.com/docs"' in pyproject
    assert "src/content/docs" not in readme


def test_docs_shims_no_longer_point_to_internal_docs_tree() -> None:
    shim_paths = [
        "docs/README.md",
        "docs/AXIOMS.md",
        "docs/CONTRIBUTING.md",
        "docs/OPERATIONS.md",
        "docs/SECURITY_TRUST_MODEL.md",
        "docs/api.md",
        "docs/architecture.md",
        "docs/archive.md",
    ]

    for rel_path in shim_paths:
        body = _read(rel_path)
        assert "https://cortexpersist.com/docs" in body
        assert "src/content/docs" not in body
