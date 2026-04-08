from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

pytest.importorskip("mcp.server.fastmcp")
sys.modules.setdefault("pyloudnorm", types.SimpleNamespace())

import cortex.mcp.server as mcp_server
from cortex.extensions.immune.filters.base import Verdict


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


class _FakeAcquire:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


class _FakePool:
    def acquire(self):
        return _FakeAcquire()


class _FakeCache:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def clear(self) -> None:
        self.data.clear()


class _FakeMetrics:
    def record_error(self, **kwargs) -> None:
        return None

    def record_request(self, **kwargs) -> None:
        return None

    def get_summary(self) -> dict[str, int]:
        return {"requests": 0}


class _FakeMembrane:
    async def intercept(self, *args, **kwargs):
        return SimpleNamespace(verdict=Verdict.PASS, risks_assumed=[])


class _FakeEngine:
    last_store_kwargs: dict[str, object] | None = None
    last_search_kwargs: dict[str, object] | None = None

    def __init__(self, db_path: str, auto_embed: bool = False) -> None:
        self._conn = None

    async def store(self, **kwargs):
        type(self).last_store_kwargs = kwargs
        return 123

    async def search(self, **kwargs):
        type(self).last_search_kwargs = kwargs
        return []


def _ctx() -> SimpleNamespace:
    async def ensure_ready() -> None:
        return None

    return SimpleNamespace(
        cfg=SimpleNamespace(db_path=":memory:", max_workers=2, query_cache_size=32),
        metrics=_FakeMetrics(),
        pool=_FakePool(),
        search_cache=_FakeCache(),
        membrane=_FakeMembrane(),
        ensure_ready=ensure_ready,
    )


@pytest.mark.asyncio
async def test_mcp_store_uses_keyword_contract(monkeypatch) -> None:
    fake_mcp = _FakeMCP()
    ctx = _ctx()
    monkeypatch.setattr(mcp_server, "CortexEngine", _FakeEngine)

    mcp_server._register_store_tool(fake_mcp, ctx)
    tool = fake_mcp.tools["cortex_store"]

    result = await tool(
        project="alpha",
        content="stored via mcp",
        fact_type="decision",
        tags='["tag-a"]',
        source="mcp-test",
        parent_decision_id=7,
    )

    assert "Stored fact #123" in result
    assert _FakeEngine.last_store_kwargs == {
        "project": "alpha",
        "content": "stored via mcp",
        "fact_type": "decision",
        "tags": ["tag-a"],
        "confidence": "stated",
        "source": "mcp-test",
        "parent_decision_id": 7,
    }


@pytest.mark.asyncio
async def test_mcp_search_uses_keyword_contract(monkeypatch) -> None:
    fake_mcp = _FakeMCP()
    ctx = _ctx()
    monkeypatch.setattr(mcp_server, "CortexEngine", _FakeEngine)

    mcp_server._register_search_tool(fake_mcp, ctx)
    tool = fake_mcp.tools["cortex_search"]

    result = await tool(query="where is alpha", project="alpha", top_k=7)

    assert result == "No results found."
    assert _FakeEngine.last_search_kwargs == {
        "query": "where is alpha",
        "project": "alpha",
        "top_k": 7,
    }


class _FakeLedger:
    def __init__(self, db) -> None:
        self.db = db

    async def audit_integrity_async(self) -> dict[str, object]:
        return {"valid": True, "tx_count": 11}


@pytest.mark.asyncio
async def test_mcp_ledger_verify_accepts_tx_count_shape(monkeypatch) -> None:
    fake_mcp = _FakeMCP()
    ctx = _ctx()
    monkeypatch.setattr(mcp_server, "ImmutableLedger", _FakeLedger)

    mcp_server._register_ledger_tool(fake_mcp, ctx)
    tool = fake_mcp.tools["cortex_ledger_verify"]

    result = await tool()

    assert "Transactions verified: 11" in result
    assert "Roots checked: 0" in result
