from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from cortex.extensions.daemon.monitors.signals import SignalMonitor
from cortex.extensions.signals.models import Signal
from cortex.extensions.signals.reactor import SignalReactor


def _make_signal(*, tenant_id: str = "tenant-a") -> Signal:
    return Signal(
        id=1,
        event_type="fact:stored",
        payload={"fact_id": 1},
        source="tests",
        project="proj-a",
        tenant_id=tenant_id,
        created_at=datetime.fromisoformat("2026-04-14T00:00:00+00:00"),
        consumed_by=[],
    )


def test_signal_monitor_emits_alerts_with_tenant_context() -> None:
    seen: dict[str, str] = {}
    signal = _make_signal()

    async def process_once(*, tenant_id: str | None = None) -> int:
        seen["tenant_id"] = tenant_id or ""
        return 1

    monitor = SignalMonitor(db_path=":memory:", tenant_id="tenant-a")
    monitor._reactor = SimpleNamespace(
        bus=SimpleNamespace(
            peek=lambda **kwargs: [signal],
        ),
        process_once=process_once,
    )

    alerts = monitor.check()

    assert seen["tenant_id"] == "tenant-a"
    assert len(alerts) == 1
    assert alerts[0].tenant_id == "tenant-a"
    assert alerts[0].project == "proj-a"
    assert alerts[0].payload == {"fact_id": 1}


@pytest.mark.asyncio
async def test_signal_reactor_polls_the_configured_tenant() -> None:
    seen: dict[str, str] = {}

    class FakeBus:
        def poll(self, **kwargs):
            seen["tenant_id"] = kwargs["tenant_id"]
            return []

    reactor = SignalReactor(FakeBus(), tenant_id="tenant-b")

    count = await reactor.process_once()

    assert count == 0
    assert seen["tenant_id"] == "tenant-b"
