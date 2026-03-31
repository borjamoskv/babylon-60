from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from cortex.cli import browser_cmds
from cortex.extensions.browser.agent import SovereignBrowserAgent
from cortex.mcp import server as mcp_server
from cortex.mcp.utils import MCPServerConfig


@pytest.mark.asyncio
async def test_browser_agent_accepts_legacy_id_for_type_action() -> None:
    agent = SovereignBrowserAgent(objective="Fill the field", llm_provider=object())
    agent.max_steps = 2
    agent.engine = SimpleNamespace(
        start=AsyncMock(),
        goto=AsyncMock(),
        parse_dom=AsyncMock(return_value={"dom": "[7] <input> Query"}),
        click=AsyncMock(),
        type=AsyncMock(),
        stop=AsyncMock(),
    )
    agent._decide_next_action = AsyncMock(
        side_effect=[
            {"cmd": "type", "id": 7, "text": "cortex"},
            {"cmd": "done", "result": "ok"},
        ]
    )

    await agent.run("https://example.com")

    agent.engine.type.assert_awaited_once_with(7, "cortex")


def test_browser_cli_surf_passes_headless_to_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured["provider_kwargs"] = kwargs

    class DummyAgent:
        def __init__(self, objective, llm_provider=None, headless=False):
            captured["objective"] = objective
            captured["llm_provider"] = llm_provider
            captured["headless"] = headless

        async def run(self, url: str):
            captured["url"] = url

    def fake_asyncio_run(coro):
        captured["asyncio_run_called"] = True
        coro.close()
        return None

    monkeypatch.setattr(browser_cmds, "SovereignBrowserAgent", DummyAgent)
    monkeypatch.setattr(browser_cmds.asyncio, "run", fake_asyncio_run)

    import cortex.extensions.llm.provider as provider_module

    monkeypatch.setattr(provider_module, "LLMProvider", DummyProvider)

    result = CliRunner().invoke(
        browser_cmds.browser,
        ["surf", "https://example.com", "--objective", "Scan page", "--headless"],
    )

    assert result.exit_code == 0
    assert captured["headless"] is True
    assert captured["objective"] == "Scan page"


def test_create_mcp_server_defaults_to_core_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class DummyMCP:
        def __init__(self, *_args, **_kwargs):
            self._registered: list[str] = []

        def tool(self):
            def decorator(fn):
                self._registered.append(fn.__name__)
                return fn

            return decorator

    def mark(name: str):
        def _inner(*_args, **_kwargs):
            calls.append(name)

        return _inner

    monkeypatch.setattr(mcp_server, "_MCP_AVAILABLE", True)
    monkeypatch.setattr(mcp_server, "FastMCP", DummyMCP)
    monkeypatch.setattr(mcp_server, "_register_store_tool", mark("store"))
    monkeypatch.setattr(mcp_server, "_register_search_tool", mark("search"))
    monkeypatch.setattr(mcp_server, "_register_status_tool", mark("status"))
    monkeypatch.setattr(mcp_server, "_register_ledger_tool", mark("ledger"))
    monkeypatch.setattr(mcp_server, "_register_trace_episode_tool", mark("trace_episode"))
    monkeypatch.setattr(mcp_server, "_register_trace_chain_tool", mark("trace_chain"))
    monkeypatch.setattr(mcp_server, "_register_shannon_report_tool", mark("shannon"))
    monkeypatch.setattr(mcp_server, "_register_handoff_tool", mark("handoff"))
    monkeypatch.setattr(mcp_server, "_register_embed_tool", mark("embed"))
    monkeypatch.setattr(mcp_server, "_register_embed_status_tool", mark("embed_status"))
    monkeypatch.setattr(mcp_server, "register_trust_tools", mark("trust"))
    monkeypatch.setattr(mcp_server, "register_mega_tools", mark("mega"))
    monkeypatch.setattr(mcp_server, "register_genesis_tools", mark("genesis"))
    monkeypatch.setattr(mcp_server, "register_health_tools", mark("health"))
    monkeypatch.setattr(mcp_server, "register_scraper_tools", mark("scraper"))

    monkeypatch.setitem(
        sys.modules,
        "cortex.mcp.hilbert_tools",
        types.SimpleNamespace(register_hilbert_tools=mark("hilbert")),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.mcp.music_tools",
        types.SimpleNamespace(register_music_tools=mark("music")),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.mcp.suno_tools",
        types.SimpleNamespace(register_suno_tools=mark("suno")),
    )

    mcp = mcp_server.create_mcp_server(MCPServerConfig(tool_profile="core"))

    assert isinstance(mcp, DummyMCP)
    assert calls == [
        "store",
        "search",
        "status",
        "ledger",
        "trace_episode",
        "trace_chain",
        "shannon",
        "handoff",
        "embed",
        "embed_status",
    ]


def test_create_mcp_server_registers_ops_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class DummyMCP:
        def __init__(self, *_args, **_kwargs):
            self._registered: list[str] = []

        def tool(self):
            def decorator(fn):
                self._registered.append(fn.__name__)
                return fn

            return decorator

    def mark(name: str):
        def _inner(*_args, **_kwargs):
            calls.append(name)

        return _inner

    monkeypatch.setattr(mcp_server, "_MCP_AVAILABLE", True)
    monkeypatch.setattr(mcp_server, "FastMCP", DummyMCP)
    monkeypatch.setattr(mcp_server, "register_mega_tools", mark("mega"))
    monkeypatch.setattr(mcp_server, "register_genesis_tools", mark("genesis"))
    monkeypatch.setattr(mcp_server, "register_scraper_tools", mark("scraper"))

    mcp = mcp_server.create_mcp_server(MCPServerConfig(tool_profile="ops"))

    assert isinstance(mcp, DummyMCP)
    assert calls == ["mega", "genesis", "scraper"]


def test_create_mcp_server_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="Unknown MCP tool profile"):
        mcp_server.create_mcp_server(MCPServerConfig(tool_profile="invalid"))


def test_profile_tool_snapshots_are_deterministic() -> None:
    assert mcp_server.get_profile_tool_names("core") == (
        "cortex_store",
        "cortex_search",
        "cortex_status",
        "cortex_ledger_verify",
        "cortex_trace_episode",
        "cortex_trace_chain",
        "cortex_shannon_report",
        "cortex_handoff",
        "cortex_embed",
        "cortex_embed_status",
    )
    assert mcp_server.get_profile_tool_names("trust") == (
        "cortex_audit_trail",
        "cortex_verify_fact",
        "cortex_compliance_report",
        "cortex_decision_lineage",
        "cortex_health_check",
        "cortex_health_report",
    )
    assert mcp_server.get_profile_tool_names("ops") == (
        "cortex_reality_weaver",
        "cortex_entropy_cracker",
        "cortex_temporal_nexus",
        "cortex_genesis_create",
        "cortex_genesis_preview",
        "cortex_genesis_templates",
        "cortex_genesis_specs",
        "cortex_scrape",
        "cortex_scrape_batch",
        "cortex_scrape_map",
    )
