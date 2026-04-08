from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.sidecar.telemetry.iot_oracle import IoTOracle


@pytest.mark.asyncio
async def test_inject_physical_intent_uses_async_store() -> None:
    engine = SimpleNamespace(store=AsyncMock())
    oracle = IoTOracle(engine=engine)

    await oracle._inject_physical_intent(
        friction_type="thermal_drop",
        severity="P2",
        metrics={"temperature": 17.9},
    )

    engine.store.assert_awaited_once()
    assert engine.store.await_args.kwargs["fact_type"] == "physical_telemetry"
    assert engine.store.await_args.kwargs["meta"]["friction_type"] == "thermal_drop"


@pytest.mark.asyncio
async def test_start_stop_interrupts_long_poll_interval() -> None:
    oracle = IoTOracle(engine=SimpleNamespace(), poll_interval=60.0)

    task = asyncio.create_task(oracle.start())
    await asyncio.sleep(0.02)
    await oracle.stop()
    await asyncio.wait_for(task, timeout=0.2)


@pytest.mark.asyncio
async def test_process_telemetry_resets_simulated_temperature_after_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle = IoTOracle(engine=SimpleNamespace())
    oracle._sim_temp = 17.9
    inject = AsyncMock()
    monkeypatch.setattr(oracle, "_inject_physical_intent", inject)

    await oracle._process_telemetry()

    inject.assert_awaited_once()
    assert oracle._sim_temp == 22.0
