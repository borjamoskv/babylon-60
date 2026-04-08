from __future__ import annotations

import asyncio

from cortex.mcp import aether_server


class _FakeResult:
    def __init__(self) -> None:
        self.fact_id = 7
        self.project = "alpha"
        self.fact_type = "decision"
        self.score = 0.99
        self.content = "tenant scoped result"


class _FakeEngine:
    all_search_calls: list[dict[str, object]] = []
    all_store_calls: list[dict[str, object]] = []

    def __init__(self, *args, **kwargs) -> None:
        self._conn = None

    async def search(self, **kwargs):
        type(self).all_search_calls.append(kwargs)
        result = _FakeResult()
        result.content = f"tenant scoped result for {kwargs['tenant_id']}"
        return [result]

    async def store(self, **kwargs):
        type(self).all_store_calls.append(kwargs)
        return 42


class _FakeConn:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _FakePool:
    def __init__(self) -> None:
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    def acquire(self):
        return _FakeConn()


class _FakeCache:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def clear(self) -> None:
        self._data.clear()


class _FakeMetrics:
    def record_request(self) -> None:
        return None


class _FakeCtx:
    def __init__(self) -> None:
        self.db_path = "/tmp/aether.db"
        self.pool = _FakePool()
        self.search_cache = _FakeCache()
        self.metrics = _FakeMetrics()
        self._initialized = False

    async def ensure_ready(self) -> None:
        if not self._initialized:
            await self.pool.initialize()
            self._initialized = True


def test_cortex_search_memory_uses_tenant_in_search_and_cache(monkeypatch) -> None:
    monkeypatch.setattr(aether_server, "CortexEngine", _FakeEngine)
    _FakeEngine.all_search_calls.clear()

    ctx = _FakeCtx()

    result_one = asyncio.run(
        aether_server._cortex_search_memory(
            ctx,
            query="memory graph",
            project="alpha",
            top_k=10,
            tenant_id="tenant-a",
        )
    )
    result_two = asyncio.run(
        aether_server._cortex_search_memory(
            ctx,
            query="memory graph",
            project="alpha",
            top_k=10,
            tenant_id="tenant-b",
        )
    )

    assert "tenant-a" in result_one
    assert "tenant-b" in result_two
    assert result_one != result_two
    assert _FakeEngine.all_search_calls == [
        {
            "query": "memory graph",
            "tenant_id": "tenant-a",
            "project": "alpha",
            "top_k": 10,
        },
        {
            "query": "memory graph",
            "tenant_id": "tenant-b",
            "project": "alpha",
            "top_k": 10,
        },
    ]


def test_cortex_store_decision_uses_tenant(monkeypatch) -> None:
    monkeypatch.setattr(aether_server, "CortexEngine", _FakeEngine)
    monkeypatch.setattr(aether_server, "_axiom_3_verify", lambda *args, **kwargs: True)
    _FakeEngine.all_store_calls.clear()

    ctx = _FakeCtx()
    result = asyncio.run(
        aether_server._cortex_store_decision(
            ctx,
            project="alpha",
            decision="Choose append-only ledger",
            tenant_id="tenant-a",
        )
    )

    assert "tenant=tenant-a" in result
    assert _FakeEngine.all_store_calls == [
        {
            "project": "alpha",
            "content": "Choose append-only ledger",
            "tenant_id": "tenant-a",
            "fact_type": "decision",
            "tags": ["mcp-aether"],
            "confidence": "stated",
            "source": "agent:gemini:aether",
        }
    ]
