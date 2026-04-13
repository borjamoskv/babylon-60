from __future__ import annotations

from cortex.extensions.daemon.loops_mixin import LoopsMixin


class _FakeStopEvent:
    def __init__(self, owner: object, stop_after: int) -> None:
        self._owner = owner
        self._stop_after = stop_after
        self.timeouts: list[float] = []

    def wait(self, timeout: float) -> None:
        self.timeouts.append(timeout)
        if len(self.timeouts) >= self._stop_after:
            self._owner._shutdown = True  # type: ignore[attr-defined]


class _FakeDaemon(LoopsMixin):
    def __init__(self, *, stop_after: int = 2) -> None:
        self._shutdown = False
        self._shared_engine = object()
        self._last_alerts: dict[str, float] = {}
        self._cooldown = 0.0
        self.notify_enabled = True
        self.notifications: list[tuple[str, str]] = []
        self._stop_event = _FakeStopEvent(self, stop_after=stop_after)

    def _send_notification(self, title: str, body: str) -> None:
        self.notifications.append((title, body))


def test_run_health_loop_backs_off_then_recovers(monkeypatch) -> None:
    persisted: list[dict] = []

    class _FakeHealthLoop:
        def __init__(self, db_path: str, notify_fn=None) -> None:
            self._interval = 5.0
            self._ticks = iter(
                [
                    None,
                    {"score": 91.0, "grade": "A", "degraded_features": []},
                ]
            )

        def tick(self):
            return next(self._ticks)

        def persist_snapshot(self, engine: object, data: dict) -> None:
            persisted.append(data)

    monkeypatch.setattr("cortex.extensions.daemon.health_loop.HealthLoop", _FakeHealthLoop)

    daemon = _FakeDaemon(stop_after=2)
    daemon._run_health_loop()

    assert daemon._stop_event.timeouts == [10.0, 5.0]
    assert persisted == [{"score": 91.0, "grade": "A", "degraded_features": []}]
    assert daemon.notifications == [
        ("CORTEX Health Monitor", "Health tick failed. Backoff now at 10s.")
    ]


def test_run_health_loop_caps_backoff_and_notifies_on_crash(monkeypatch) -> None:
    class _ExplodingHealthLoop:
        def __init__(self, db_path: str, notify_fn=None) -> None:
            self._interval = 2000.0

        def tick(self):
            raise RuntimeError("collector exploded")

        def persist_snapshot(self, engine: object, data: dict) -> None:
            raise AssertionError("persist_snapshot should not run on crashes")

    monkeypatch.setattr("cortex.extensions.daemon.health_loop.HealthLoop", _ExplodingHealthLoop)

    daemon = _FakeDaemon(stop_after=1)
    daemon._run_health_loop()

    assert daemon._stop_event.timeouts == [3600.0]
    assert daemon.notifications == [
        ("CORTEX Health Monitor", "Critical health loop error: collector exploded")
    ]
