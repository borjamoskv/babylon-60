"""Tests for cortex/utils/sanitize.py — target 100% coverage."""
from __future__ import annotations

import pytest

from cortex.utils.sanitize import (
    MAX_QUERY_LENGTH,
    ALLOWED_FACT_TYPES,
    sanitize_project_name,
    sanitize_query,
    sanitize_tenant_id,
    validate_fact_type,
    validate_pagination,
)


# ─── sanitize_project_name ────────────────────────────────────────────


class TestSanitizeProjectName:
    def test_valid_simple(self):
        assert sanitize_project_name("my-project") == "my-project"

    def test_valid_with_dots(self):
        assert sanitize_project_name("project.v1") == "project.v1"

    def test_valid_alphanumeric(self):
        assert sanitize_project_name("Project123") == "Project123"

    def test_strips_whitespace(self):
        assert sanitize_project_name("  myproj  ") == "myproj"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_project_name("")

    def test_null_byte_raises(self):
        with pytest.raises(ValueError, match="forbidden"):
            sanitize_project_name("proj\x00name")

    def test_newline_raises(self):
        with pytest.raises(ValueError, match="forbidden"):
            sanitize_project_name("proj\nname")

    def test_tab_raises(self):
        with pytest.raises(ValueError, match="forbidden"):
            sanitize_project_name("proj\tname")

    def test_escape_char_raises(self):
        with pytest.raises(ValueError, match="forbidden"):
            sanitize_project_name("proj\x1bname")

    def test_starts_with_dash_raises(self):
        with pytest.raises(ValueError, match="Invalid project name"):
            sanitize_project_name("-bad")

    def test_starts_with_dot_raises(self):
        with pytest.raises(ValueError, match="Invalid project name"):
            sanitize_project_name(".bad")

    def test_unicode_normalization(self):
        # NFKC normalizes certain Unicode sequences
        result = sanitize_project_name("proj1")
        assert result == "proj1"

    def test_max_length_valid(self):
        name = "a" + "b" * 127  # 128 chars starting with alpha
        result = sanitize_project_name(name)
        assert len(result) == 128

    def test_too_long_raises(self):
        name = "a" * 129
        with pytest.raises(ValueError, match="Invalid project name"):
            sanitize_project_name(name)

    def test_special_chars_raises(self):
        with pytest.raises(ValueError, match="Invalid project name"):
            sanitize_project_name("proj name")  # space not allowed


# ─── sanitize_tenant_id ───────────────────────────────────────────────


class TestSanitizeTenantId:
    def test_empty_returns_default(self):
        assert sanitize_tenant_id("") == "default"

    def test_valid_lowercase(self):
        assert sanitize_tenant_id("tenant_01") == "tenant_01"

    def test_valid_with_dash(self):
        assert sanitize_tenant_id("tenant-01") == "tenant-01"

    def test_valid_mixed_case(self):
        # regex has IGNORECASE so uppercase is ok
        result = sanitize_tenant_id("MyTenant")
        assert result == "MyTenant"

    def test_invalid_space_raises(self):
        with pytest.raises(ValueError, match="Invalid tenant_id"):
            sanitize_tenant_id("bad tenant")

    def test_invalid_too_long_raises(self):
        with pytest.raises(ValueError, match="Invalid tenant_id"):
            sanitize_tenant_id("a" * 65)

    def test_strips_whitespace(self):
        result = sanitize_tenant_id("  t1  ")
        assert result == "t1"


# ─── sanitize_query ───────────────────────────────────────────────────


class TestSanitizeQuery:
    def test_valid_query(self):
        result = sanitize_query("find me something")
        assert result == "find me something"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_query("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            sanitize_query("   ")

    def test_strips_dangerous_chars(self):
        result = sanitize_query("hello\x00world")
        assert "\x00" not in result
        assert "hello" in result

    def test_strips_carriage_return(self):
        result = sanitize_query("query\rtext")
        assert "\r" not in result

    def test_strips_newline(self):
        result = sanitize_query("query\ntext")
        assert "\n" not in result

    def test_strips_tab(self):
        result = sanitize_query("query\ttext")
        assert "\t" not in result

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="too long"):
            sanitize_query("a" * (MAX_QUERY_LENGTH + 1))

    def test_max_length_exactly_ok(self):
        result = sanitize_query("a" * MAX_QUERY_LENGTH)
        assert len(result) == MAX_QUERY_LENGTH

    def test_unicode_normalization(self):
        result = sanitize_query("caf\u00e9")
        assert result == "café"


# ─── validate_fact_type ───────────────────────────────────────────────


class TestValidateFactType:
    @pytest.mark.parametrize("ft", sorted(ALLOWED_FACT_TYPES))
    def test_all_allowed_types(self, ft):
        assert validate_fact_type(ft) == ft

    def test_strips_whitespace(self):
        assert validate_fact_type("  knowledge  ") == "knowledge"

    def test_lowercases(self):
        assert validate_fact_type("KNOWLEDGE") == "knowledge"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid fact_type"):
            validate_fact_type("banana")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Invalid fact_type"):
            validate_fact_type("")


# ─── validate_pagination ─────────────────────────────────────────────


class TestValidatePagination:
    def test_defaults(self):
        limit, offset = validate_pagination()
        assert limit == 50
        assert offset == 0

    def test_valid_values(self):
        limit, offset = validate_pagination(limit=10, offset=5)
        assert limit == 10
        assert offset == 5

    def test_limit_below_one_clamps_to_one(self):
        limit, offset = validate_pagination(limit=0)
        assert limit == 1

    def test_limit_negative_clamps_to_one(self):
        limit, offset = validate_pagination(limit=-5)
        assert limit == 1

    def test_limit_above_max_clamps(self):
        limit, offset = validate_pagination(limit=9999, max_limit=100)
        assert limit == 100

    def test_offset_negative_clamps_to_zero(self):
        limit, offset = validate_pagination(offset=-10)
        assert offset == 0

    def test_custom_max_limit(self):
        limit, offset = validate_pagination(limit=500, max_limit=200)
        assert limit == 200

    def test_limit_exactly_max(self):
        limit, _ = validate_pagination(limit=1000)
        assert limit == 1000
