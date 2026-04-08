from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

import pytest

from cortex.database.schema_extensions import CREATE_LLM_TELEMETRY
from cortex.extensions.llm._models import CascadeEvent, CascadeTier, IntentProfile
from cortex.extensions.llm._telemetry import CascadeTelemetry
from cortex.extensions.nexus.db import NexusDB
from cortex.extensions.nexus.types import DomainOrigin, IntentType, WorldMutation


def test_cascade_telemetry_normalizes_datetime_timestamp(tmp_path) -> None:
    db_path = tmp_path / "telemetry.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(CREATE_LLM_TELEMETRY)
        conn.commit()

    telemetry = CascadeTelemetry(str(db_path))
    ts = datetime(2026, 4, 7, 12, 30, 45, tzinfo=timezone.utc)
    telemetry.emit(
        CascadeEvent(
            intent=IntentProfile.CODE,
            resolved_by="provider-a",
            tier=CascadeTier.PRIMARY,
            depth=1,
            latency_ms=12.5,
            timestamp=ts,
        )
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT timestamp FROM llm_telemetry").fetchone()

    assert row is not None
    assert row[0] == pytest.approx(ts.timestamp())


def test_nexus_db_normalizes_date_timestamp_for_insert_and_query(tmp_path) -> None:
    db_path = tmp_path / "nexus.db"
    db = NexusDB(str(db_path))

    assert db.insert(
        WorldMutation(
            origin=DomainOrigin.CORTEX_CORE,
            intent=IntentType.DECISION_STORED,
            project="proj",
            payload={"fact_id": 7},
            timestamp=date(2026, 4, 7),
        )
    )

    expected = datetime(2026, 4, 7, tzinfo=timezone.utc).timestamp()
    rows = db.query(project="proj", since=date(2026, 4, 7))

    assert len(rows) == 1
    assert rows[0]["timestamp"] == pytest.approx(expected)
