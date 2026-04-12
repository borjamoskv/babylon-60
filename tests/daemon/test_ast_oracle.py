from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.daemon.sidecar.telemetry import ast_oracle as ast_module
from cortex.extensions.daemon.sidecar.telemetry.ast_oracle import ASTOracle


@pytest.mark.asyncio
async def test_stop_interrupts_long_poll_interval_and_joins_observer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    joined = {"value": False}
    stopped = {"value": False}

    class _Observer:
        def schedule(self, *args, **kwargs) -> None:
            return None

        def start(self) -> None:
            return None

        def stop(self) -> None:
            stopped["value"] = True

        def join(self) -> None:
            joined["value"] = True

    monkeypatch.setattr(ast_module, "Observer", _Observer)

    oracle = ASTOracle(
        engine=SimpleNamespace(store=AsyncMock()), watch_dir=tmp_path, poll_interval=60
    )
    monkeypatch.setattr(oracle, "_pre_warm_cache", AsyncMock())

    async def _idle_process_events() -> None:
        return None

    monkeypatch.setattr(oracle, "_process_events", _idle_process_events)

    task = asyncio.create_task(oracle.start())
    await asyncio.sleep(0.02)
    await oracle.stop()
    await asyncio.wait_for(task, timeout=0.3)

    assert stopped["value"] is True
    assert joined["value"] is True


@pytest.mark.asyncio
async def test_process_events_removes_deleted_files_from_cache(tmp_path) -> None:
    oracle = ASTOracle(engine=SimpleNamespace(store=AsyncMock()), watch_dir=tmp_path)
    removed = tmp_path / "gone.py"
    oracle._event_queue = asyncio.Queue()
    await oracle._event_queue.put(removed)
    oracle._mtimes[str(removed)] = 1.0
    oracle._cache[str(removed)] = {"node"}

    await oracle._process_events()

    assert str(removed) not in oracle._mtimes
    assert str(removed) not in oracle._cache
