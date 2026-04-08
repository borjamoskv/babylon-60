from __future__ import annotations

import importlib
import sys

import pytest

pytest.importorskip("mcp.server.fastmcp")


def test_mcp_server_imports_without_optional_music_dependencies() -> None:
    for module_name in (
        "pyloudnorm",
        "cortex.mcp.server",
        "cortex.mcp.music_tools",
        "cortex.extensions.music_engine",
        "cortex.extensions.music_engine.orchestrator",
        "cortex.extensions.music_engine.dsp_apotheosis",
    ):
        sys.modules.pop(module_name, None)

    module = importlib.import_module("cortex.mcp.server")

    assert module.mcp is None
    server = module.create_mcp_server()
    assert server is not None
