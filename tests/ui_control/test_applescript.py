from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.ui_control.applescript import run_applescript
from cortex.extensions.ui_control.models import AppleScriptExecutionError


@pytest.mark.asyncio
async def test_run_applescript_returns_none_when_osascript_is_unavailable_and_non_strict(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _missing_binary(*args, **kwargs):
        raise FileNotFoundError("osascript not found")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _missing_binary)

    with caplog.at_level("WARNING"):
        result = await run_applescript('return "ok"', require_success=False)

    assert result is None
    assert "AppleScript unavailable" in caplog.text


@pytest.mark.asyncio
async def test_run_applescript_raises_execution_error_when_osascript_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _missing_binary(*args, **kwargs):
        raise FileNotFoundError("osascript not found")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _missing_binary)

    with pytest.raises(AppleScriptExecutionError) as exc_info:
        await run_applescript('return "ok"', require_success=True)

    assert exc_info.value.returncode == -1
    assert "osascript not found" in exc_info.value.stderr


@pytest.mark.asyncio
async def test_run_applescript_timeout_returns_none_in_non_strict_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = MagicMock()
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    process.wait = AsyncMock()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))

    result = await run_applescript('return "ok"', require_success=False, timeout=0.01)

    assert result is None
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()
