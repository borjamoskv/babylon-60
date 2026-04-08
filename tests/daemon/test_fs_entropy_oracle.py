from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.sidecar.telemetry.fs_entropy_oracle import FSEntropyOracle


@pytest.mark.asyncio
async def test_measure_entropy_persists_growth_with_async_store(tmp_path) -> None:
    target = tmp_path / "entropy"
    target.mkdir()
    (target / "seed.txt").write_text("seed", encoding="utf-8")

    engine = SimpleNamespace(store=AsyncMock())
    oracle = FSEntropyOracle(
        engine=engine,
        target_dir=target,
        entropy_threshold_mb=0.0,
    )

    await oracle._measure_entropy()
    (target / "growth.txt").write_text("x" * 4096, encoding="utf-8")
    await oracle._measure_entropy()

    engine.store.assert_awaited_once()
    call = engine.store.await_args
    assert call.kwargs["project"] == "SYSTEM"
    assert call.kwargs["fact_type"] == "ghost"
    assert call.kwargs["meta"]["oracle"] == "fs_entropy_v1"
    assert call.kwargs["meta"]["delta_mb"] > 0


@pytest.mark.asyncio
async def test_start_logs_failures_and_continues_until_stopped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    oracle = FSEntropyOracle(
        engine=SimpleNamespace(),
        target_dir=tmp_path,
        poll_interval=0.01,
    )

    calls = {"count": 0}

    async def flaky_measure() -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        await oracle.stop()

    monkeypatch.setattr(oracle, "_measure_entropy", flaky_measure)

    with caplog.at_level("WARNING"):
        await asyncio.wait_for(oracle.start(), timeout=0.2)

    assert calls["count"] >= 2
    assert "FSEntropyOracle cycle failed: boom" in caplog.text


@pytest.mark.asyncio
async def test_stop_interrupts_long_poll_interval(tmp_path) -> None:
    oracle = FSEntropyOracle(
        engine=SimpleNamespace(),
        target_dir=tmp_path,
        poll_interval=60.0,
    )

    task = asyncio.create_task(oracle.start())
    await asyncio.sleep(0.02)
    await oracle.stop()
    await asyncio.wait_for(task, timeout=0.2)


@pytest.mark.asyncio
async def test_measure_entropy_warns_when_engine_cannot_persist(
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target = tmp_path / "entropy"
    target.mkdir()
    (target / "seed.txt").write_text("seed", encoding="utf-8")

    oracle = FSEntropyOracle(
        engine=SimpleNamespace(),
        target_dir=target,
        entropy_threshold_mb=0.0,
    )

    await oracle._measure_entropy()
    (target / "growth.txt").write_text("x" * 2048, encoding="utf-8")

    with caplog.at_level("WARNING"):
        await oracle._measure_entropy()

    assert "FSEntropyOracle skipped persistence: engine lacks store/store_sync" in caplog.text
