from __future__ import annotations

import asyncio


def test_connect_toolbox_skips_default_localhost_without_env(monkeypatch) -> None:
    import cortex.adk.runner as adk_runner
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    monkeypatch.delenv("TOOLBOX_URL", raising=False)

    class FailingBridge:
        def __init__(self, config) -> None:  # noqa: ANN001
            raise AssertionError("default local toolbox should be skipped when not configured")

    monkeypatch.setattr(toolbox_bridge, "ToolboxBridge", FailingBridge)

    assert asyncio.run(adk_runner._connect_toolbox()) == []


def test_toolbox_bridge_connect_returns_false_on_os_error(monkeypatch) -> None:
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    class FailingClient:
        def __init__(self, server_url: str) -> None:
            self.server_url = server_url

        async def load_toolset(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise OSError(f"connect call failed {self.server_url}")

    monkeypatch.setattr(toolbox_bridge, "_TOOLBOX_AVAILABLE", True)
    monkeypatch.setattr(toolbox_bridge, "ToolboxClient", FailingClient)

    bridge = toolbox_bridge.ToolboxBridge(toolbox_bridge.ToolboxConfig())

    assert asyncio.run(bridge.connect()) is False
    assert bridge.tools == []
