from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.frontier import FrontierDaemon


@pytest.mark.asyncio
async def test_log_evolution_uses_async_store() -> None:
    engine = SimpleNamespace(store=AsyncMock())
    daemon = FrontierDaemon(engine=engine)

    await daemon._log_evolution("ingestion", "Analyzed source")

    engine.store.assert_awaited_once()
    kwargs = engine.store.await_args.kwargs
    assert kwargs["project"] == "cortex"
    assert kwargs["fact_type"] == "decision"
    assert kwargs["source"] == "daemon:frontier"


@pytest.mark.asyncio
async def test_run_loop_stop_interrupts_sleep() -> None:
    daemon = FrontierDaemon(engine=None, metabolism_interval_hours=24, ingestion_interval_hours=24)

    async def _stop() -> None:
        daemon.stop()

    daemon._run_metabolism = _stop  # type: ignore[method-assign]
    daemon._run_ingestion = AsyncMock()  # type: ignore[method-assign]

    await asyncio.wait_for(daemon.run_loop(), timeout=0.2)


@pytest.mark.asyncio
async def test_log_evolution_warns_without_store_capability(
    caplog: pytest.LogCaptureFixture,
) -> None:
    daemon = FrontierDaemon(engine=SimpleNamespace())

    with caplog.at_level("WARNING"):
        await daemon._log_evolution("metabolism", "noop")

    assert "[FRONTIER] Skipped evolution log: engine lacks store/store_sync" in caplog.text
