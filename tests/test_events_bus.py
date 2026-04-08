from __future__ import annotations

import pytest

from cortex.events.bus import DistributedEventBus


@pytest.mark.asyncio
async def test_event_bus_logs_subscriber_failures_without_stopping_delivery(caplog) -> None:
    bus = DistributedEventBus()
    seen: list[dict[str, object]] = []

    async def _ok(payload: dict[str, object]) -> None:
        seen.append(payload.copy())

    async def _boom(payload: dict[str, object]) -> None:
        raise RuntimeError("subscriber down")

    bus.subscribe("topic.test", _ok)
    bus.subscribe("topic.test", _boom)

    with caplog.at_level("WARNING"):
        await bus.publish("topic.test", {"hello": "world"})

    assert len(seen) == 1
    assert seen[0]["hello"] == "world"
    assert seen[0]["_topic"] == "topic.test"
    assert any("failed for topic topic.test" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_event_bus_signal_persistence_failure_does_not_block_subscribers(caplog) -> None:
    bus = DistributedEventBus()
    seen: list[dict[str, object]] = []

    class _BrokenSignalBus:
        def emit(self, **kwargs) -> int:
            raise RuntimeError("sqlite down")

    async def _ok(payload: dict[str, object]) -> None:
        seen.append(payload.copy())

    bus.attach_signal_bus(_BrokenSignalBus())
    bus.subscribe("topic.test", _ok)

    with caplog.at_level("WARNING"):
        await bus.publish("topic.test", {"hello": "world"})

    assert len(seen) == 1
    assert any("Signal Bus persistence failed for topic topic.test" in msg for msg in caplog.messages)
