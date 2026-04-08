import sys
from unittest.mock import MagicMock

import pytest

from cortex.gateway import GatewayIntent, GatewayRequest
from cortex.gateway.handlers.gidatu import GidatuHandler


@pytest.fixture(autouse=True)
def _cleanup_ghost_modules():
    for name in (
        "ghost_chain",
        "ghost_guard",
        "ghost_platform",
        "ghost_resilience",
        "ghost_vlm",
    ):
        sys.modules.pop(name, None)
    yield
    for name in (
        "ghost_chain",
        "ghost_guard",
        "ghost_platform",
        "ghost_resilience",
        "ghost_vlm",
    ):
        sys.modules.pop(name, None)


@pytest.mark.asyncio
async def test_handle_fails_cleanly_when_skill_dir_is_missing(tmp_path):
    handler = GidatuHandler(skill_name="Missing", skills_root=tmp_path)
    request = GatewayRequest(intent=GatewayIntent.GIDATU, payload={"action": "status"})

    with pytest.raises(ImportError, match=r"Missing/scripts$"):
        await handler.handle(request)


@pytest.mark.asyncio
async def test_handle_status_uses_to_thread_and_returns_handler_result(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "Gidatu" / "scripts"
    scripts_dir.mkdir(parents=True)

    handler = GidatuHandler(skills_root=tmp_path)
    runtime = {"platform_info": lambda: {"os": "darwin"}}
    sync_handle = MagicMock(return_value={"status": "ready"})

    monkeypatch.setattr(handler, "_load_runtime", lambda: runtime)
    monkeypatch.setattr(handler, "_sync_handle", sync_handle)

    request = GatewayRequest(intent=GatewayIntent.GIDATU, payload={"action": "status"})
    result = await handler.handle(request)

    assert result == {"status": "ready"}
    assert sync_handle.call_args.args[0] == runtime
    assert sync_handle.call_args.args[1] == "status"
