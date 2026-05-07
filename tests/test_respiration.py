from __future__ import annotations

import pytest

from cortex.utils.respiration import _reserve_slot, breathe, oxygenate


async def test_breathe_yields_to_event_loop() -> None:
    await breathe(0)


def test_reserve_slot_advances_from_existing_schedule() -> None:
    next_allowed = [10.0]

    assert _reserve_slot(now=9.0, next_allowed=next_allowed, interval=2.0) == 10.0
    assert next_allowed == [12.0]
    assert _reserve_slot(now=15.0, next_allowed=next_allowed, interval=2.0) == 15.0
    assert next_allowed == [17.0]


def test_oxygenate_wraps_sync_functions_without_changing_metadata() -> None:
    @oxygenate(min_interval=0)
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    assert add.__name__ == "add"
    assert add.__doc__ == "Add two numbers."
    assert add(2, 3) == 5


async def test_oxygenate_wraps_async_functions() -> None:
    calls: list[int] = []

    @oxygenate(min_interval=0)
    async def collect(value: int) -> int:
        calls.append(value)
        return value * 2

    assert await collect(4) == 8
    assert calls == [4]


def test_oxygenate_sync_delay_branch_uses_event_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []

    class FakeEvent:
        def wait(self, interval: float) -> None:
            waits.append(interval)

    monotonic_values = iter([0.0, 0.0, 0.0, 0.0, 0.0])
    monkeypatch.setattr("cortex.utils.respiration.time.monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr("cortex.utils.respiration.threading.Event", FakeEvent)

    @oxygenate(min_interval=1.0)
    def touch() -> str:
        return "ok"

    assert touch() == "ok"
    assert touch() == "ok"
    assert waits == [1.0]
