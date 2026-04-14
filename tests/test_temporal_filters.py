"""Unit tests for temporal validity helpers shared across read paths."""

from __future__ import annotations

import pytest

from cortex.memory.temporal import build_temporal_filter_params, is_valid_at, time_travel_filter


def test_is_valid_at_excludes_exact_valid_until_boundary() -> None:
    valid_from = "2026-04-14T10:00:00+00:00"
    valid_until = "2026-04-14T10:05:00+00:00"

    assert is_valid_at(valid_from, valid_until, "2026-04-14T10:04:59+00:00") is True
    assert is_valid_at(valid_from, valid_until, valid_until) is False


def test_build_temporal_filter_params_respects_valid_until_column_fallback() -> None:
    clause, params = build_temporal_filter_params(
        "2026-04-14T10:05:00+00:00",
        table_alias="f",
    )

    assert "COALESCE(json_extract(f.metadata, '$.valid_until'), f.valid_until)" in clause
    assert "COALESCE(json_extract(f.metadata, '$.tombstoned_at'), f.valid_until)" in clause
    assert params == [
        "2026-04-14T10:05:00+00:00",
        "2026-04-14T10:05:00+00:00",
        "2026-04-14T10:05:00+00:00",
    ]


def test_build_temporal_filter_params_rejects_unsafe_alias() -> None:
    with pytest.raises(ValueError, match="Invalid table alias"):
        build_temporal_filter_params("2026-04-14T10:05:00+00:00", table_alias="f;drop")


def test_time_travel_filter_requires_positive_tx_id() -> None:
    with pytest.raises(ValueError, match="Invalid tx_id"):
        time_travel_filter(0, table_alias="f")


def test_time_travel_filter_uses_valid_until_fallback_in_generated_sql() -> None:
    clause, params = time_travel_filter(7, table_alias="f")

    assert "COALESCE(json_extract(f.metadata, '$.valid_until'), f.valid_until)" in clause
    assert "COALESCE(json_extract(f.metadata, '$.tombstoned_at'), f.valid_until)" in clause
    assert params == [7, 7, 7, 7]
