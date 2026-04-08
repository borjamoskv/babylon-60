from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.zero_prompting import ZeroPromptingDaemon


@pytest.mark.asyncio
async def test_crystallize_uses_async_store(tmp_path) -> None:
    engine = SimpleNamespace(store=AsyncMock())
    daemon = ZeroPromptingDaemon(engine=engine, workspace_root=tmp_path)

    await daemon._crystallize(
        "reduce entropy",
        {"action": "heal"},
        {"net_positive": True, "delta_entropy": 2},
    )

    engine.store.assert_awaited_once()
    kwargs = engine.store.await_args.kwargs
    assert kwargs["project"] == "cortex"
    assert kwargs["fact_type"] == "decision"
    assert kwargs["source"] == "daemon:zero-prompting"


@pytest.mark.asyncio
async def test_run_loop_stop_interrupts_sleep(tmp_path) -> None:
    daemon = ZeroPromptingDaemon(
        engine=SimpleNamespace(),
        workspace_root=tmp_path,
        cycle_interval_hours=24.0,
    )

    async def _stop_cycle(*, focus: str = "entropy") -> dict[str, bool]:
        daemon.stop()
        return {"evolved": False}

    daemon.evolution_cycle = _stop_cycle  # type: ignore[method-assign]

    await asyncio.wait_for(daemon.run_loop(), timeout=0.2)


@pytest.mark.asyncio
async def test_crystallize_warns_without_store_capability(
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    daemon = ZeroPromptingDaemon(engine=SimpleNamespace(), workspace_root=Path(tmp_path))

    with caplog.at_level("WARNING"):
        await daemon._crystallize("h", {"action": "x"}, {"net_positive": True})

    assert "[ZERO-PROMPTING] Skipped crystallization: engine lacks store/store_sync" in caplog.text
