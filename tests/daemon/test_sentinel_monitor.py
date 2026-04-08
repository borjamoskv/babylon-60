from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.daemon.sidecar.sentinel_monitor import monitor as sentinel_module
from cortex.extensions.daemon.sidecar.sentinel_monitor.monitor import SentinelMonitor


@pytest.mark.asyncio
async def test_check_movements_formats_token_values_with_decimal_precision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = SentinelMonitor(check_interval=60)
    monitor._notify_os = AsyncMock()  # type: ignore[method-assign]
    monitor._log_fact = MagicMock()  # type: ignore[method-assign]

    token_tx = {
        "blockNumber": "42",
        "from": sentinel_module.TARGET_ADDRESS,
        "to": "0xdeadbeef",
        "hash": "0xtx",
        "tokenSymbol": "USDC",
        "tokenDecimal": "6",
        "value": "1234567",
    }
    fetch = AsyncMock(side_effect=[[token_tx], []])
    monkeypatch.setattr(monitor, "_fetch_txlist", fetch)

    await monitor._check_movements(SimpleNamespace())

    monitor._notify_os.assert_awaited_once()
    monitor._log_fact.assert_called_once_with("0xtx", "0xdeadbeef", "1.2345", "USDC")
    assert monitor.last_block_scanned == 42


@pytest.mark.asyncio
async def test_run_loop_stop_interrupts_long_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = SentinelMonitor(check_interval=60)

    class _Response:
        status = 200

        async def json(self) -> dict[str, str]:
            return {"result": "0x10"}

    class _RequestContext:
        async def __aenter__(self) -> _Response:
            return _Response()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    class _Session:
        def get(self, *args, **kwargs) -> _RequestContext:
            return _RequestContext()

        async def __aenter__(self) -> _Session:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(sentinel_module.aiohttp, "ClientSession", lambda: _Session())

    async def _stop_on_first_check(session) -> None:
        await monitor.stop()

    monkeypatch.setattr(monitor, "_check_movements", _stop_on_first_check)

    await asyncio.wait_for(monitor.run_loop(), timeout=0.2)
    assert monitor.last_block_scanned == 16


def test_format_asset_value_handles_invalid_payload() -> None:
    assert SentinelMonitor._format_asset_value("not-a-number", 18) == "0.0000"
