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


def test_get_toolbox_tools_returns_empty_list_when_bridge_is_unavailable(monkeypatch) -> None:
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    async def fake_cortex_self_bridge(*, toolset: str):  # noqa: ARG001
        return None

    monkeypatch.setattr(toolbox_bridge, "cortex_self_bridge", fake_cortex_self_bridge)

    assert toolbox_bridge.get_toolbox_tools() == []


def test_mcp_guard_accepts_default_toolbox_port() -> None:
    from cortex.mcp.guard import MCPGuard

    MCPGuard.validate_toolbox_url("http://127.0.0.1:5050")


def test_toolbox_config_defaults_include_guard_allowlist() -> None:
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    config = toolbox_bridge.ToolboxConfig()

    assert "http://127.0.0.1:5000" in config.allowed_server_urls
    assert "http://localhost:5000" in config.allowed_server_urls


def test_toolbox_bridge_connect_returns_false_on_disallowed_url(monkeypatch) -> None:
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    class UnexpectedClient:
        def __init__(self, server_url: str) -> None:  # noqa: ARG002
            raise AssertionError("disallowed URL should not reach ToolboxClient")

    monkeypatch.setattr(toolbox_bridge, "_TOOLBOX_AVAILABLE", True)
    monkeypatch.setattr(toolbox_bridge, "ToolboxClient", UnexpectedClient)

    bridge = toolbox_bridge.ToolboxBridge(
        toolbox_bridge.ToolboxConfig(
            server_url="http://127.0.0.1:5999",
            allowed_server_urls=[toolbox_bridge.DEFAULT_SERVER_URL],
        )
    )

    assert asyncio.run(bridge.connect()) is False
    assert bridge.tools == []


def test_connect_toolbox_degrades_on_disallowed_env_url(monkeypatch) -> None:
    import cortex.adk.runner as adk_runner
    import cortex.mcp.toolbox_bridge as toolbox_bridge

    class UnexpectedClient:
        def __init__(self, server_url: str) -> None:  # noqa: ARG002
            raise AssertionError("disallowed env URL should not reach ToolboxClient")

    monkeypatch.setenv("TOOLBOX_URL", "http://127.0.0.1:5999")
    monkeypatch.delenv("TOOLBOX_ALLOWED_URLS", raising=False)
    monkeypatch.setattr(toolbox_bridge, "_TOOLBOX_AVAILABLE", True)
    monkeypatch.setattr(toolbox_bridge, "ToolboxClient", UnexpectedClient)

    assert asyncio.run(adk_runner._connect_toolbox()) == []
