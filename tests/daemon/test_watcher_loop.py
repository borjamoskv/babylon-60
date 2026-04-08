from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.daemon.loops import watcher as watcher_module
from cortex.extensions.daemon.loops.watcher import GitWatcherHandler, git_watcher_loop


@pytest.mark.asyncio
async def test_git_watcher_loop_stops_observer_and_marks_offline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    calls = {"started": False, "stopped": False, "joined": False}

    class _Observer:
        def schedule(self, *args, **kwargs) -> None:
            return None

        def start(self) -> None:
            calls["started"] = True

        def stop(self) -> None:
            calls["stopped"] = True

        def join(self) -> None:
            calls["joined"] = True

    monkeypatch.setattr(watcher_module, "Observer", _Observer)

    state = SimpleNamespace(daemons={"git_watcher": {"status": "offline", "last_event": "N/A"}})
    osc_client = MagicMock()
    speak_func = AsyncMock()
    (tmp_path / ".git").mkdir()

    task = asyncio.create_task(
        git_watcher_loop(
            state,
            tmp_path,
            osc_client,
            speak_func,
            asyncio.get_running_loop(),
        )
    )
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls == {"started": True, "stopped": True, "joined": True}
    assert state.daemons["git_watcher"]["status"] == "offline"


@pytest.mark.asyncio
async def test_git_watcher_handler_tolerates_ghosts_without_source_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    tasks: list[asyncio.Task] = []

    def _run_coroutine_threadsafe(coro, loop):
        task = loop.create_task(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", _run_coroutine_threadsafe)

    fake_engine = SimpleNamespace(list_active_ghosts=AsyncMock(return_value=[{}]))
    monkeypatch.setattr("cortex.engine.CortexEngine", lambda: fake_engine)

    state = SimpleNamespace(
        daemons={
            "git_watcher": {"status": "online", "last_event": "N/A"},
            "ghost_field": {"resonances": [], "active_ghosts": 0},
        }
    )
    osc_client = MagicMock()
    speak_func = AsyncMock()
    handler = GitWatcherHandler(
        state,
        tmp_path,
        osc_client,
        speak_func,
        asyncio.get_running_loop(),
    )

    event = SimpleNamespace(src_path=str(tmp_path / ".git" / "HEAD"))
    handler.on_modified(event)
    await asyncio.gather(*tasks)

    osc_client.send_message.assert_called_once_with("/cortex/git_pulse", 1.0)
    speak_func.assert_awaited()
