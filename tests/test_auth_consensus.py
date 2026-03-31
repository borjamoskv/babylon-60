from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import cortex.api.state as api_state
from cortex.auth.deps import require_consensus, require_verified_permission
from cortex.auth.models import AuthResult


class StubAsyncEngine:
    def __init__(self, *, search_results=None, facts=None):
        self.search_results = search_results or []
        self.facts = facts or {}
        self.search_calls = []
        self.get_fact_calls = []

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return self.search_results

    async def get_fact(self, fact_id: int, tenant_id: str = "default"):
        self.get_fact_calls.append((fact_id, tenant_id))
        return self.facts.get(fact_id)


def _request_with_engine(engine: object) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/test",
        "headers": [],
        "app": SimpleNamespace(state=SimpleNamespace(async_engine=engine)),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_require_consensus_accepts_exact_match_for_tenant():
    engine = StubAsyncEngine(
        search_results=[SimpleNamespace(fact_id=7, content="Permission write granted to root-key")],
        facts={7: {"id": 7, "consensus_score": 0.91}},
    )

    ok = await require_consensus(
        "Permission write granted to root-key",
        engine=engine,
        tenant_id="tenant-alpha",
    )

    assert ok is True
    assert engine.search_calls == [
        {
            "query": "Permission write granted to root-key",
            "top_k": 5,
            "tenant_id": "tenant-alpha",
        }
    ]
    assert engine.get_fact_calls == [(7, "tenant-alpha")]


@pytest.mark.asyncio
async def test_require_consensus_fails_closed_without_exact_match():
    engine = StubAsyncEngine(
        search_results=[SimpleNamespace(fact_id=9, content="Permission write granted to someone-else")],
        facts={9: {"id": 9, "consensus_score": 0.99}},
    )

    ok = await require_consensus(
        "Permission write granted to root-key",
        engine=engine,
        tenant_id="tenant-alpha",
    )

    assert ok is False
    assert engine.get_fact_calls == []


@pytest.mark.asyncio
async def test_require_verified_permission_rejects_low_consensus():
    engine = StubAsyncEngine(
        search_results=[SimpleNamespace(fact_id=3, content="Permission admin granted to ops-key")],
        facts={3: {"id": 3, "consensus_score": 0.52}},
    )
    request = _request_with_engine(engine)
    checker = require_verified_permission("admin", min_consensus=0.8)

    with pytest.raises(HTTPException) as excinfo:
        await checker(
            request,
            auth=AuthResult(
                authenticated=True,
                tenant_id="tenant-ops",
                permissions=["admin"],
                key_name="ops-key",
            ),
        )

    assert excinfo.value.status_code == 403
    assert "requires consensus" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_require_verified_permission_uses_api_state_engine_fallback():
    engine = StubAsyncEngine(
        search_results=[SimpleNamespace(fact_id=11, content="Permission read granted to reader-key")],
        facts={11: {"id": 11, "consensus_score": 0.87}},
    )
    previous_engine = api_state.async_engine
    api_state.async_engine = engine
    checker = require_verified_permission("read", min_consensus=0.8)

    try:
        result = await checker(
            _request_with_engine(None),
            auth=AuthResult(
                authenticated=True,
                tenant_id="tenant-read",
                permissions=["read"],
                key_name="reader-key",
            ),
        )
    finally:
        api_state.async_engine = previous_engine

    assert result.tenant_id == "tenant-read"
