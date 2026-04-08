from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent


@pytest.mark.asyncio
async def test_event_ledger_orders_by_timestamp_not_event_id(tmp_path) -> None:
    db_path = tmp_path / "ledger_ordering.db"
    async with aiosqlite.connect(db_path) as conn:
        ledger = EventLedgerL3(conn)

        base = datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc)
        late = MemoryEvent(
            event_id="aaa",
            timestamp=base + timedelta(seconds=10),
            role="assistant",
            content="late",
            token_count=1,
            session_id="s1",
            tenant_id="tenant-a",
        )
        early = MemoryEvent(
            event_id="zzz",
            timestamp=base,
            role="user",
            content="early",
            token_count=1,
            session_id="s1",
            tenant_id="tenant-a",
        )

        await ledger.append_event(late)
        await ledger.append_event(early)

        session_events = await ledger.get_session_events("s1", tenant_id="tenant-a")
        replayed = await ledger.replay("tenant-a")
        audit = await ledger.verify_chain("tenant-a")

    assert [event.content for event in session_events] == ["early", "late"]
    assert [event.content for event in replayed] == ["early", "late"]
    assert audit["status"] == "VALID"
