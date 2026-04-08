from __future__ import annotations

from cortex.mcp.utils import MCPServerConfig


def test_adk_tools_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    from cortex.adk import tools as adk_tools

    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    assert adk_tools._get_db_path() == str(preferred)


def test_adk_tools_falls_back_to_legacy_env(monkeypatch, tmp_path) -> None:
    from cortex.adk import tools as adk_tools

    fallback = tmp_path / "fallback.db"
    monkeypatch.delenv("CORTEX_DB_PATH", raising=False)
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    assert adk_tools._get_db_path() == str(fallback)


def test_mcp_server_config_respects_db_path_alias(monkeypatch, tmp_path) -> None:
    preferred = tmp_path / "preferred.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(preferred))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    cfg = MCPServerConfig()

    assert cfg.db_path == str(preferred)
