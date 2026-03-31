"""Unit tests for Toolbox bridge compatibility helpers."""

from __future__ import annotations

from types import SimpleNamespace

from cortex.mcp.toolbox_bridge import ToolboxBridge, ToolboxConfig, _patch_toolbox_schema_types


def test_patch_toolbox_schema_types_adds_number() -> None:
    """Current Toolbox servers emit JSON Schema `number` for float params."""
    protocol_module = SimpleNamespace(__TYPE_MAP={"string": str})

    _patch_toolbox_schema_types(protocol_module)

    assert protocol_module.__TYPE_MAP["number"] is float


def test_tool_names_prefer_dunder_name() -> None:
    """toolbox-core exposes tool names via `__name__`, not `.name`."""
    bridge = ToolboxBridge(ToolboxConfig())
    bridge._tools = [  # pyright: ignore[reportPrivateUsage]
        SimpleNamespace(__name__="query-facts"),
        SimpleNamespace(name="legacy-name"),
    ]

    assert bridge.tool_names == ["query-facts", "legacy-name"]
