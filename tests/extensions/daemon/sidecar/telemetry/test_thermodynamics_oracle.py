from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from cortex.extensions.daemon.sidecar.telemetry import thermodynamics_oracle as thermo_module
from cortex.extensions.daemon.sidecar.telemetry.thermodynamics_oracle import ThermodynamicsOracle


class AsyncEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def store(self, **payload: object) -> None:
        self.calls.append(payload)


class SyncStoreEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def store(self, **payload: object) -> None:
        self.calls.append(payload)


class FakeTask:
    def __init__(self, name: str, coro_name: str, *, done: bool = False) -> None:
        self._name = name
        self._coro_name = coro_name
        self._done = done
        self.cancelled = False

    def get_name(self) -> str:
        return self._name

    def get_coro(self) -> SimpleNamespace:
        return SimpleNamespace(__name__=self._coro_name)

    def cancel(self) -> None:
        self.cancelled = True

    def done(self) -> bool:
        return self._done


@pytest.mark.asyncio
async def test_sample_persists_critical_event_with_async_store(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = AsyncEngine()
    oracle = ThermodynamicsOracle(engine, poll_interval=60.0)
    oracle._cores = 1

    monkeypatch.setattr(thermo_module.os, "getloadavg", lambda: (1.0, 1.0, 1.0))
    monkeypatch.setattr(thermo_module.asyncio, "all_tasks", lambda: {asyncio.current_task()})
    monkeypatch.setattr(oracle, "_execute_annihilation_protocol", lambda: 3)

    await oracle._sample_thermodynamics(lag_ms=600.0)

    assert len(engine.calls) == 1
    payload = engine.calls[0]
    assert payload["fact_type"] == "thermal_noise"
    assert "THERMODYNAMIC COLLAPSE" in str(payload["content"])
    assert payload["meta"]["severity"] == "CRITICAL"  # type: ignore[index]
    assert payload["meta"]["purged_tasks"] == 3  # type: ignore[index]
    assert oracle.poll_interval == 15.0


@pytest.mark.asyncio
async def test_sample_accepts_sync_store_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SyncStoreEngine()
    oracle = ThermodynamicsOracle(engine, poll_interval=60.0, thermal_threshold=0.5)
    oracle._cores = 1

    monkeypatch.setattr(thermo_module.os, "getloadavg", lambda: (1.0, 1.0, 1.0))
    monkeypatch.setattr(thermo_module.asyncio, "all_tasks", lambda: {asyncio.current_task()})

    await oracle._sample_thermodynamics(lag_ms=0.0)

    assert len(engine.calls) == 1
    payload = engine.calls[0]
    assert payload["fact_type"] == "thermal_noise"
    assert payload["meta"]["severity"] == "HIGH"  # type: ignore[index]
    assert oracle.poll_interval == 15.0


@pytest.mark.asyncio
async def test_start_logs_sampling_failures(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    oracle = ThermodynamicsOracle(engine=object(), poll_interval=0.0)

    async def boom() -> float:
        oracle._running = False
        raise RuntimeError("sensor jammed")

    monkeypatch.setattr(oracle, "_measure_event_loop_lag", boom)

    with caplog.at_level(logging.WARNING):
        await oracle.start()

    assert "sensor jammed" in caplog.text


def test_annihilation_protocol_skips_critical_and_finished_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle = ThermodynamicsOracle(engine=object())

    current = FakeTask("current", "sample")
    worker = FakeTask("worker-task", "compute")
    server = FakeTask("server-watch", "watch_loop")
    finished = FakeTask("finished-task", "compute", done=True)

    monkeypatch.setattr(thermo_module.asyncio, "current_task", lambda: current)
    monkeypatch.setattr(
        thermo_module.asyncio,
        "all_tasks",
        lambda: {current, worker, server, finished},
    )

    purged = oracle._execute_annihilation_protocol()

    assert purged == 1
    assert worker.cancelled is True
    assert server.cancelled is False
    assert finished.cancelled is False
