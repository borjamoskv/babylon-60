from __future__ import annotations

import threading

import pytest

from cortex.extensions.daemon.core import MoskvDaemon
from cortex.extensions.daemon.sidecar.telemetry.fiat_oracle import FiatOracle
from cortex.extensions.daemon.sidecar.trends_oracle.config import TrendsConfig


def test_fiat_oracle_sync_loop_stop_wakes_interval(monkeypatch, tmp_path) -> None:
    """The threaded fiat sidecar should not wait for its full interval after stop()."""
    oracle = FiatOracle(engine=object(), interval=60.0)
    oracle.queue_dir = tmp_path
    checked = threading.Event()

    def check_once() -> None:
        checked.set()
        oracle.stop()

    monkeypatch.setattr(oracle, "_check_signals_sync", check_once)

    thread = threading.Thread(target=oracle.run_sync_loop)
    thread.start()

    assert checked.wait(2.0)
    thread.join(2.0)
    assert not thread.is_alive()


def test_trends_oracle_sync_loop_stop_wakes_interval(monkeypatch) -> None:
    """The threaded trends sidecar should not wait for its full poll interval after stop()."""
    trends_module = pytest.importorskip(
        "cortex.extensions.daemon.sidecar.trends_oracle.oracle",
        reason="Google Trends optional dependencies are not installed",
    )

    monkeypatch.setattr(trends_module, "TrendReq", lambda *args, **kwargs: object())

    oracle = trends_module.TrendsOracle(
        engine=None,
        config=TrendsConfig(enable_realtime=False, daily_interval=0),
    )
    checked = threading.Event()

    def poll_once() -> None:
        checked.set()
        oracle.stop()

    monkeypatch.setattr(oracle, "_poll_daily_sync", poll_once)

    thread = threading.Thread(target=oracle.run_sync_loop)
    thread.start()

    assert checked.wait(2.0)
    thread.join(2.0)
    assert not thread.is_alive()


async def test_sovereign_shutdown_stops_fiat_oracle() -> None:
    """Daemon shutdown should propagate stop() to the fiat sidecar thread."""

    class StopRecorder:
        stopped = False

        def stop(self) -> None:
            self.stopped = True

    daemon = MoskvDaemon.__new__(MoskvDaemon)
    daemon.watchdog_hub = None
    daemon.scheduler = None
    daemon._event_bus = None
    daemon.fiat_oracle = StopRecorder()
    daemon.entropic_wake_daemon = None
    daemon.frontier_daemon = None
    daemon.zero_prompting_daemon = None
    daemon.epistemic_breaker_daemon = None
    daemon.hot_state = None

    await MoskvDaemon._sovereign_shutdown(daemon)

    assert daemon.fiat_oracle.stopped
