"""Focused tests for the legacy Aether MCP server surface."""

from cortex.mcp.aether_server import create_aether_server


def test_aether_server_registers_only_expected_tools() -> None:
    server = create_aether_server()

    tool_names = set(server._tool_manager._tools)

    assert tool_names == {
        "cortex_search_memory",
        "cortex_read_file",
        "cortex_store_decision",
        "cortex_get_swarm_report",
    }


def test_aether_server_does_not_expose_shell_execution() -> None:
    server = create_aether_server()

    tool_names = set(server._tool_manager._tools)

    assert "cortex_execute_bash" not in tool_names
    assert not any("bash" in name or "shell" in name or "exec" in name for name in tool_names)
