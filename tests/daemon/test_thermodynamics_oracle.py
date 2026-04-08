from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.sidecar.telemetry.thermodynamics_oracle import ThermodynamicsOracle


@pytest.mark.asyncio
async def test_store_thermal_noise_uses_async_store() -> None:
    engine = SimpleNamespace(store=AsyncMock())
    oracle = ThermodynamicsOracle(engine=engine)

    stored = await oracle._store_thermal_noise("thermal event", {"severity": "HIGH"})

    assert stored is True
    engine.store.assert_awaited_once_with(
        project="SYSTEM",
        content="thermal event",
        fact_type="thermal_noise",
        meta={"severity": "HIGH"},
    )


@pytest.mark.asyncio
async def test_sample_warns_when_engine_cannot_persist(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    oracle = ThermodynamicsOracle(engine=SimpleNamespace(), thermal_threshold=0.1)
    oracle._psutil = None
    oracle._cores = 1

    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("os.getloadavg", lambda: (2.0, 1.0, 1.0))

    with caplog.at_level("WARNING"):
        await oracle._sample_thermodynamics(lag_ms=600.0)

    assert "ThermodynamicsOracle skipped persistence: engine lacks store/store_sync" in caplog.text


@pytest.mark.asyncio
async def test_stop_interrupts_long_poll_interval() -> None:
    oracle = ThermodynamicsOracle(engine=SimpleNamespace(), poll_interval=60.0)

    task = asyncio.create_task(oracle.start())
    await asyncio.sleep(0.12)
    await oracle.stop()
    await asyncio.wait_for(task, timeout=0.3)


@pytest.mark.asyncio
async def test_start_logs_cycle_failures_and_recovers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    oracle = ThermodynamicsOracle(engine=SimpleNamespace(), poll_interval=0.01)
    calls = {"count": 0}

    async def _flaky_sample(lag_ms: float) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("thermal boom")
        await oracle.stop()

    monkeypatch.setattr(oracle, "_sample_thermodynamics", _flaky_sample)

    with caplog.at_level("WARNING"):
        await asyncio.wait_for(oracle.start(), timeout=0.3)

    assert calls["count"] >= 2
    assert "ThermodynamicsOracle cycle failed: thermal boom" in caplog.text
