from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from cortex.database import schema as db_schema
from cortex.extensions.timing.tracker import TimingTracker


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(db_schema.CREATE_HEARTBEATS)
    conn.executescript(db_schema.CREATE_HEARTBEATS_INDEX)
    conn.executescript(db_schema.CREATE_TIME_ENTRIES)
    conn.executescript(db_schema.CREATE_TIME_ENTRIES_INDEX)
    return conn


def test_heartbeat_normalizes_aware_datetime_before_sqlite_bind() -> None:
    conn = _make_conn()
    tracker = TimingTracker(conn)
    ts = datetime(2026, 4, 7, 12, 34, 56, tzinfo=timezone.utc)

    tracker.heartbeat("proj", "file.py", timestamp=ts)

    stored = conn.execute("SELECT timestamp FROM heartbeats").fetchone()[0]
    assert stored == "2026-04-07T12:34:56+00:00"


def test_heartbeat_normalizes_naive_datetime_as_utc() -> None:
    conn = _make_conn()
    tracker = TimingTracker(conn)
    ts = datetime(2026, 4, 7, 12, 34, 56)

    tracker.heartbeat("proj", "file.py", timestamp=ts)

    stored = conn.execute("SELECT timestamp FROM heartbeats").fetchone()[0]
    assert stored == "2026-04-07T12:34:56+00:00"


def test_heartbeat_normalizes_date_to_utc_midnight() -> None:
    conn = _make_conn()
    tracker = TimingTracker(conn)

    tracker.heartbeat("proj", "file.py", timestamp=date(2026, 4, 7))

    stored = conn.execute("SELECT timestamp FROM heartbeats").fetchone()[0]
    assert stored == "2026-04-07T00:00:00+00:00"
