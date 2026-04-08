from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.autopoiesis import (
    AutopoiesisCycleResult,
    AutopoiesisDaemon,
    AutopoiesisEngine,
    AutopoiesisSnapshot,
)


def test_plan_selects_heal_when_score_below_target(tmp_path) -> None:
    engine = AutopoiesisEngine(engine=None, workspace_root=tmp_path)
    snapshot = AutopoiesisSnapshot(
        timestamp=time.time(),
        workspace_root=str(tmp_path),
        entropy_score=20.0,
        scan_score=80,
        registered_tools=0,
    )

    plan = engine.plan(snapshot)

    assert plan.action == "heal"
    assert "below target" in plan.rationale


@pytest.mark.asyncio
async def test_run_cycle_accepts_improvement_and_crystallizes(tmp_path) -> None:
    store = AsyncMock()
    sink = SimpleNamespace(store=store)
    engine = AutopoiesisEngine(engine=sink, workspace_root=tmp_path)
    before = AutopoiesisSnapshot(
        timestamp=time.time(),
        workspace_root=str(tmp_path),
        entropy_score=20.0,
        scan_score=80,
        registered_tools=0,
    )
    after = AutopoiesisSnapshot(
        timestamp=time.time(),
        workspace_root=str(tmp_path),
        entropy_score=5.0,
        scan_score=95,
        registered_tools=0,
    )

    engine.observe = AsyncMock(return_value=before)  # type: ignore[method-assign]
    engine.act = AsyncMock(return_value={"success": True, "performed": True})  # type: ignore[method-assign]
    engine.measure = AsyncMock(  # type: ignore[method-assign]
        return_value=(
            after,
            {
                "net_positive": True,
                "delta_entropy": 15.0,
                "delta_score": 15,
                "delta_tools": 0,
                "performed": True,
            },
        )
    )

    result = await engine.run_cycle()

    assert result.accepted is True
    assert result.action == "heal"
    store.assert_awaited_once()
    kwargs = store.await_args.kwargs
    assert kwargs["project"] == "cortex"
    assert kwargs["source"] == "daemon:autopoiesis"
    assert kwargs["fact_type"] == "decision"


@pytest.mark.asyncio
async def test_run_loop_stop_interrupts_sleep(tmp_path) -> None:
    result = AutopoiesisCycleResult(
        evolved=False,
        accepted=False,
        action="stabilize",
        hypothesis="stable",
        improvement={"net_positive": False, "performed": False},
        snapshot_before=AutopoiesisSnapshot(
            timestamp=time.time(),
            workspace_root=str(tmp_path),
            entropy_score=0.0,
        ),
        snapshot_after=AutopoiesisSnapshot(
            timestamp=time.time(),
            workspace_root=str(tmp_path),
            entropy_score=0.0,
        ),
        action_result={"success": True, "performed": False},
    )

    daemon: AutopoiesisDaemon | None = None

    async def _run_cycle(*, focus: str = "entropy") -> AutopoiesisCycleResult:
        assert focus == "entropy"
        assert daemon is not None
        daemon.stop()
        return result

    stub_engine = SimpleNamespace(
        policy=SimpleNamespace(focus="entropy"),
        run_cycle=AsyncMock(side_effect=_run_cycle),
    )
    daemon = AutopoiesisDaemon(
        engine=None,
        workspace_root=tmp_path,
        cycle_interval_hours=24.0,
        autopoiesis_engine=stub_engine,
    )

    await asyncio.wait_for(daemon.run_loop(), timeout=0.2)
    stub_engine.run_cycle.assert_awaited_once()
