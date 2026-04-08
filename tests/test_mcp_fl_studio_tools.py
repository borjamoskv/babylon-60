from __future__ import annotations

from typing import Any

import pytest

from cortex.mcp.fl_studio_tools import _normalize_bpm, register_fl_studio_tools


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeBridge:
    def __init__(self, *, write_enabled: bool = False) -> None:
        self.write_enabled = write_enabled
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def invoke(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(params or {})
        self.calls.append((action, payload))

        if action == "session.status":
            return {
                "ok": True,
                "data": {
                    "project_name": "My FL Project",
                    "connected": True,
                },
            }

        if action == "transport.status":
            return {
                "ok": True,
                "data": {
                    "playing": True,
                    "tempo_bpm": "126.5",
                    "song_position": "3:02:20",
                },
            }

        if action == "mixer.channels.list":
            return {
                "ok": True,
                "data": {
                    "channels": ["Kick", "Lead"],
                },
            }

        if action == "transport.play":
            return {"ok": True, "message": "FL Studio transport started."}

        if action == "transport.stop":
            return {"ok": True, "message": "FL Studio transport stopped."}

        if action == "project.tempo.set":
            return {
                "ok": True,
                "message": f"FL Studio tempo set to {payload['tempo_bpm']} BPM.",
            }

        raise AssertionError(f"Unexpected action {action}")


@pytest.mark.asyncio
async def test_fl_studio_status_reports_bridge_state() -> None:
    fake_mcp = _FakeMCP()
    bridge = _FakeBridge()

    register_fl_studio_tools(fake_mcp, bridge=bridge)
    tool = fake_mcp.tools["fl_studio_status"]

    result = await tool()

    assert "FL Studio bridge ready" in result
    assert "Project: My FL Project" in result
    assert "Write enabled: False" in result
    assert bridge.calls == [("session.status", {})]


@pytest.mark.asyncio
async def test_fl_studio_list_channels_formats_results() -> None:
    fake_mcp = _FakeMCP()
    bridge = _FakeBridge()

    register_fl_studio_tools(fake_mcp, bridge=bridge)
    tool = fake_mcp.tools["fl_studio_list_channels"]

    result = await tool()

    assert result == "FL Studio channels:\n- Kick\n- Lead"


@pytest.mark.asyncio
async def test_fl_studio_set_tempo_uses_normalized_decimal() -> None:
    fake_mcp = _FakeMCP()
    bridge = _FakeBridge(write_enabled=True)

    register_fl_studio_tools(fake_mcp, bridge=bridge)
    tool = fake_mcp.tools["fl_studio_set_tempo"]

    result = await tool("126.500")

    assert result == "FL Studio tempo set to 126.5 BPM."
    assert bridge.calls == [("project.tempo.set", {"tempo_bpm": "126.5"})]


@pytest.mark.asyncio
async def test_fl_studio_set_tempo_rejects_invalid_range() -> None:
    fake_mcp = _FakeMCP()
    bridge = _FakeBridge(write_enabled=True)

    register_fl_studio_tools(fake_mcp, bridge=bridge)
    tool = fake_mcp.tools["fl_studio_set_tempo"]

    result = await tool("310")

    assert result == "❌ Rejected by Guard: BPM must be between 20 and 300."
    assert bridge.calls == []


@pytest.mark.asyncio
async def test_fl_studio_tools_explain_missing_configuration() -> None:
    fake_mcp = _FakeMCP()

    register_fl_studio_tools(fake_mcp, bridge=None)
    tool = fake_mcp.tools["fl_studio_status"]

    result = await tool()

    assert "FL Studio bridge not configured." in result


def test_normalize_bpm_strips_trailing_zeroes() -> None:
    assert _normalize_bpm("128.000") == "128"
