"""
CORTEX v5.0 — Temporal Fact Management.

Handles versioned facts with valid_from/valid_until semantics.
Never deletes — only deprecates. Enables time-travel queries.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TypeAlias

__all__ = [
    "build_temporal_filter_params",
    "is_valid_at",
    "normalize_timestamp",
    "normalize_timestamp_epoch",
    "now_iso",
    "time_travel_filter",
]

TimestampInput: TypeAlias = str | date | datetime | None
EpochTimestampInput: TypeAlias = float | int | str | date | datetime | None


def _metadata_fallback(prefix: str, field: str) -> str:
    """Return a JSON fallback expression that tolerates encrypted metadata blobs."""
    return (
        f"CASE WHEN {prefix}metadata LIKE 'v6_aesgcm:%' THEN NULL "
        f"ELSE json_extract({prefix}metadata, '$.{field}') END"
    )


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def normalize_timestamp(value: TimestampInput) -> str | None:
    """Normalize supported timestamp inputs to a stable string representation."""
    if value is None or isinstance(value, str):
        return value

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat()

    midnight_utc = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return midnight_utc.isoformat()


def normalize_timestamp_epoch(value: EpochTimestampInput) -> float | None:
    """Normalize supported timestamp inputs to UTC epoch seconds."""
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid timestamp")

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            iso_value = value.replace("Z", "+00:00")
            value = datetime.fromisoformat(iso_value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.timestamp()

    midnight_utc = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return midnight_utc.timestamp()


def is_valid_at(valid_from: str, valid_until: str | None, at: str | None = None) -> bool:
    """Check if a fact is valid at a specific point in time.

    Args:
        valid_from: ISO 8601 timestamp when fact became valid.
        valid_until: ISO 8601 timestamp when fact was deprecated (None = still valid).
        at: ISO 8601 timestamp to check against (None = now).

    Returns:
        True if the fact was valid at the given time.
    """
    check_time = at or now_iso()

    if valid_from > check_time:
        return False

    if valid_until is not None and valid_until <= check_time:
        return False

    return True


def build_temporal_filter_params(
    as_of: str | None = None,
    table_alias: str | None = None,
) -> tuple[str, list]:
    """Build parameterized SQL WHERE clause for temporal filtering.

    Args:
        as_of: ISO 8601 timestamp. None = current facts only.
        table_alias: Optional table alias prefix (e.g. "f" → "f.valid_from").
                     If None, uses bare column names.

    Returns:
        Tuple of (SQL WHERE clause, parameters list).

    Raises:
        ValueError: If table_alias contains non-alphanumeric characters.
    """
    # Defense-in-depth: whitelist the alias to prevent injection
    if table_alias is not None:
        if not table_alias.isalnum():
            raise ValueError(f"Invalid table alias: {table_alias!r}")
        prefix = f"{table_alias}."
    else:
        prefix = ""

    if as_of is None:
        return f"{prefix}is_tombstoned = 0", []
    else:
        valid_from_expr = (
            f"coalesce({prefix}valid_from, {_metadata_fallback(prefix, 'valid_from')}, "
            f"{prefix}created_at)"
        )
        valid_until_expr = (
            f"coalesce({prefix}valid_until, {_metadata_fallback(prefix, 'valid_until')})"
        )
        tombstoned_at_expr = (
            f"coalesce({prefix}tombstoned_at, {_metadata_fallback(prefix, 'tombstoned_at')})"
        )
        return (
            f"{valid_from_expr} <= ? AND "
            f"({prefix}is_tombstoned = 0 OR {valid_until_expr} > ? OR "
            f"{tombstoned_at_expr} > ?)",
            [as_of, as_of, as_of],
        )


def time_travel_filter(
    tx_id: int,
    table_alias: str | None = None,
) -> tuple[str, list]:
    """Build SQL WHERE clause to reconstruct fact state at a specific transaction.

    Returns facts whose ``tx_id`` is at or before the target transaction
    and that had not yet been deprecated at that point.

    Args:
        tx_id: Transaction ID to travel to.
        table_alias: Optional table alias prefix.

    Returns:
        Tuple of (SQL WHERE clause, parameters list).

    Raises:
        ValueError: If tx_id is not a positive integer or alias is unsafe.
    """
    if not isinstance(tx_id, int) or tx_id <= 0:
        raise ValueError(f"Invalid tx_id: {tx_id!r}")

    if table_alias is not None:
        if not table_alias.isalnum():
            raise ValueError(f"Invalid table alias: {table_alias!r}")
        prefix = f"{table_alias}."
    else:
        prefix = ""

    tx_id_expr = f"coalesce({prefix}tx_id, {_metadata_fallback(prefix, 'tx_id')})"
    valid_until_expr = f"coalesce({prefix}valid_until, {_metadata_fallback(prefix, 'valid_until')})"
    tombstoned_at_expr = (
        f"coalesce({prefix}tombstoned_at, {_metadata_fallback(prefix, 'tombstoned_at')})"
    )

    return (
        f"{tx_id_expr} <= ? AND ("  # nosec B608
        f"{prefix}is_tombstoned = 0 OR "
        f"{valid_until_expr} > (SELECT timestamp FROM transactions WHERE id = ?) OR "
        f"{tombstoned_at_expr} > (SELECT timestamp FROM transactions WHERE id = ?))",
        [tx_id, tx_id, tx_id],
    )
