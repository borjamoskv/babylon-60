from __future__ import annotations

from pathlib import Path

import pytest

from cortex.database.core import connect as db_connect
from cortex.extensions.signals.bus import SignalBus
from cortex.extensions.signals.fact_hook import emit_fact_stored


def test_fact_hook_and_signal_bus_are_tenant_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "signals.db"
    monkeypatch.setenv("CORTEX_COMPACT_THRESHOLD", "2")

    emit_fact_stored(
        db_path=str(db_path),
        fact_id=1,
        project="shared-project",
        fact_type="knowledge",
        source="test-suite",
        tenant_id="tenant_a",
    )
    emit_fact_stored(
        db_path=str(db_path),
        fact_id=2,
        project="shared-project",
        fact_type="knowledge",
        source="test-suite",
        tenant_id="tenant_b",
    )

    conn = db_connect(str(db_path))
    try:
        bus = SignalBus(conn)
        bus.ensure_table()

        history_a = bus.history(tenant_id="tenant_a", project="shared-project", limit=10)
        history_b = bus.history(tenant_id="tenant_b", project="shared-project", limit=10)

        assert [sig.event_type for sig in history_a] == ["fact:stored"]
        assert [sig.event_type for sig in history_b] == ["fact:stored"]

        emit_fact_stored(
            db_path=str(db_path),
            fact_id=3,
            project="shared-project",
            fact_type="knowledge",
            source="test-suite",
            tenant_id="tenant_a",
        )

        history_a = bus.history(tenant_id="tenant_a", project="shared-project", limit=10)
        history_b = bus.history(tenant_id="tenant_b", project="shared-project", limit=10)

        assert [sig.event_type for sig in history_a] == ["compact:needed", "fact:stored", "fact:stored"]
        assert [sig.event_type for sig in history_b] == ["fact:stored"]
    finally:
        conn.close()
