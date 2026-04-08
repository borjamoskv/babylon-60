from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.daemon.loops import peripherals as peripherals_module


@pytest.mark.asyncio
async def test_scan_peripherals_once_parses_airpods(monkeypatch: pytest.MonkeyPatch) -> None:
    process = MagicMock()
    process.communicate = AsyncMock(
        return_value=(b"AirPods\nBattery Level: 87%\nConnected: Yes\n", b"")
    )

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_shell",
        AsyncMock(return_value=process),
    )

    state = SimpleNamespace(daemons={"peripherals": {"devices": {}}})
    await peripherals_module._scan_peripherals_once(state)

    assert state.daemons["peripherals"]["devices"]["AirPods"]["battery"] == 87
    assert state.daemons["peripherals"]["devices"]["AirPods"]["connected"] is True


@pytest.mark.asyncio
async def test_scan_peripherals_once_kills_process_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    process = MagicMock()
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    process.wait = AsyncMock()

    monkeypatch.setattr(
        asyncio,
        "create_subprocess_shell",
        AsyncMock(return_value=process),
    )

    state = SimpleNamespace(daemons={"peripherals": {"devices": {}}})
    with caplog.at_level("WARNING"):
        await peripherals_module._scan_peripherals_once(state, command_timeout=0.01)

    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
    assert "Peripheral scan timed out" in caplog.text
