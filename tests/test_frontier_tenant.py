from __future__ import annotations

import asyncio

from cortex.audit.frontier import FrontierAuditor


class _FakeFact:
    def __init__(self, fact_id: int, type_name: str, content: str) -> None:
        self.id = fact_id
        self.type_name = type_name
        self.content = content


class _FakeEngine:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.store_calls: list[dict[str, object]] = []

    def search_sync(self, **kwargs):
        self.search_calls.append(kwargs)
        return [_FakeFact(1, "decision", "tenant-scoped fact")]

    def store_sync(self, **kwargs):
        self.store_calls.append(kwargs)
        return 123


class _FakeResponse:
    def __init__(self, content: str, provider: str = "fake") -> None:
        self.ok = True
        self.content = content
        self.provider = provider
        self.latency_ms = 1.0


class _FakeLLM:
    responses = iter(
        [
            _FakeResponse("tom"),
            _FakeResponse("benji"),
            _FakeResponse("oliver"),
        ]
    )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def generate(self, **kwargs):
        return next(type(self).responses)


def test_frontier_auditor_threads_tenant_into_search_and_store(monkeypatch) -> None:
    engine = _FakeEngine()
    monkeypatch.setattr("cortex.audit.frontier.SovereignLLM", lambda **kwargs: _FakeLLM())

    auditor = FrontierAuditor(engine=engine, tenant_id="tenant-a")
    result = asyncio.run(auditor.run_audit("alpha"))

    assert result["status"] == "SUCCESS"
    assert engine.search_calls == [
        {
            "query": "project:alpha",
            "tenant_id": "tenant-a",
            "top_k": 100,
        }
    ]
    assert engine.store_calls == [
        {
            "tenant_id": "tenant-a",
            "project": "alpha",
            "fact_type": "audit_report",
            "content": result["report_markdown"],
            "confidence": 0.95,
        }
    ]
