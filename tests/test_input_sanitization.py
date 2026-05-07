from __future__ import annotations

import pytest

from cortex.utils.sanitize import (
    MAX_QUERY_LENGTH,
    sanitize_project_name,
    sanitize_query,
    sanitize_tenant_id,
    validate_fact_type,
    validate_pagination,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" cortex-alpha_01 ", "cortex-alpha_01"),
        ("Project.Name-1", "Project.Name-1"),
        ("Ａgent_01", "Agent_01"),
    ],
)
def test_sanitize_project_name_normalizes_safe_names(raw: str, expected: str) -> None:
    assert sanitize_project_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "../escape",
        "-starts-with-dash",
        "has spaces",
        "tenant\nbreak",
        "x" * 129,
    ],
)
def test_sanitize_project_name_rejects_unsafe_names(raw: str) -> None:
    with pytest.raises(ValueError):
        sanitize_project_name(raw)


def test_sanitize_tenant_id_uses_default_for_empty_value() -> None:
    assert sanitize_tenant_id("") == "default"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" tenant-alpha ", "tenant-alpha"),
        ("TENANT_01", "TENANT_01"),
        ("ｔenant-01", "tenant-01"),
    ],
)
def test_sanitize_tenant_id_normalizes_safe_ids(raw: str, expected: str) -> None:
    assert sanitize_tenant_id(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "tenant.with.dot",
        "tenant/slash",
        "tenant\nline",
        "x" * 65,
    ],
)
def test_sanitize_tenant_id_rejects_unsafe_ids(raw: str) -> None:
    with pytest.raises(ValueError, match="Invalid tenant_id"):
        sanitize_tenant_id(raw)


def test_sanitize_query_strips_control_characters_after_normalization() -> None:
    assert sanitize_query("  alpha\nbeta\tgamma  ") == "alphabetagamma"


@pytest.mark.parametrize("raw", ["", "   ", "\n\t"])
def test_sanitize_query_rejects_empty_queries(raw: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        sanitize_query(raw)


def test_sanitize_query_rejects_oversized_queries() -> None:
    with pytest.raises(ValueError, match="Query too long"):
        sanitize_query("x" * (MAX_QUERY_LENGTH + 1))


def test_validate_fact_type_normalizes_allowed_values() -> None:
    assert validate_fact_type(" Decision ") == "decision"


def test_validate_fact_type_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Invalid fact_type"):
        validate_fact_type("admin_override")


@pytest.mark.parametrize(
    ("limit", "offset", "expected"),
    [
        (None, None, (50, 0)),
        (0, -10, (1, 0)),
        (5000, 7, (1000, 7)),
        (12, 3, (12, 3)),
    ],
)
def test_validate_pagination_clamps_bounds(
    limit: int | None, offset: int | None, expected: tuple[int, int]
) -> None:
    assert validate_pagination(limit, offset) == expected
