from __future__ import annotations

import asyncio
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon


def _engine_with_conn(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(pool=SimpleNamespace(get_connection=lambda: conn))


def test_check_entropy_uses_current_fact_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE facts (
            fact_type TEXT,
            confidence TEXT,
            is_tombstoned INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.executemany(
        "INSERT INTO facts (fact_type, confidence, is_tombstoned) VALUES (?, ?, ?)",
        [
            ("ghost", "stated", 0),
            ("decision", "C2", 0),
            ("ghost", "C5", 1),
        ],
    )
    conn.commit()

    daemon = EntropicWakeDaemon(_engine_with_conn(conn))

    sensor = SimpleNamespace(scan_field=lambda path: [{"strength": 2.0}])
    monkeypatch.setattr(
        "cortex.extensions.daemon.entropic_wake.TopographicSensor",
        lambda: sensor,
    )

    entropy = daemon.check_entropy()

    assert entropy == pytest.approx(0.45)


@pytest.mark.asyncio
async def test_log_action_to_cortex_uses_async_store() -> None:
    engine = SimpleNamespace(store=AsyncMock())
    daemon = EntropicWakeDaemon(engine)

    await daemon._log_action_to_cortex("router")

    engine.store.assert_awaited_once()
    kwargs = engine.store.await_args.kwargs
    assert kwargs["project"] == "cortex"
    assert kwargs["fact_type"] == "decision"
    assert kwargs["source"] == "daemon:entropic-wake"


@pytest.mark.asyncio
async def test_run_loop_stop_interrupts_long_sleep() -> None:
    daemon = EntropicWakeDaemon(engine=None, check_interval_hours=24)
    daemon.check_entropy = lambda: 0.0  # type: ignore[method-assign]

    task = asyncio.create_task(daemon.run_loop())
    await asyncio.sleep(0.02)
    daemon.stop()
    await asyncio.wait_for(task, timeout=0.2)
