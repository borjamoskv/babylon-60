from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.gateway import GatewayIntent, GatewayRequest, GatewayRouter


@pytest.mark.asyncio
async def test_gateway_router_store_success():
    """Verify that GatewayRouter accurately routes STORE intent."""
    mock_engine = AsyncMock()
    mock_engine.store.return_value = "fact_123"

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(
        intent=GatewayIntent.STORE,
        project="test_proj",
        payload={"content": "test content", "type": "knowledge"},
    )

    resp = await router.handle(req)

    assert resp.ok is True
    assert resp.data["fact_id"] == "fact_123"
    mock_engine.store.assert_called_once_with(
        project="test_proj",
        content="test content",
        tenant_id="default",
        fact_type="knowledge",
        tags=[],
        confidence="stated",
        source="api",
    )


@pytest.mark.asyncio
async def test_gateway_router_invalid_intent():
    """Verify that GatewayRouter fails gracefully on unknown intent."""
    mock_engine = MagicMock()
    router = GatewayRouter(engine=mock_engine)

    # Bypass enum for testing
    req = GatewayRequest(intent="invalid_intent", payload={})  # type: ignore

    resp = await router.handle(req)

    assert resp.ok is False
    assert "Unknown intent" in resp.error


@pytest.mark.asyncio
async def test_gateway_router_exception_handling():
    """Verify that GatewayRouter captures and returns handler exceptions."""
    mock_engine = AsyncMock()
    mock_engine.search.side_effect = ValueError("Mocked DB failure")

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.SEARCH, payload={"query": "test query"})

    resp = await router.handle(req)

    assert resp.ok is False
    assert "Mocked DB failure" in resp.error
    assert resp.latency_ms > 0


@pytest.mark.asyncio
async def test_gateway_router_recall_forwards_tenant_id():
    mock_engine = AsyncMock()
    mock_engine.recall.return_value = []

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(
        intent=GatewayIntent.RECALL,
        project="test_proj",
        tenant_id="tenant-42",
    )

    resp = await router.handle(req)

    assert resp.ok is True
    mock_engine.recall.assert_called_once_with("test_proj", tenant_id="tenant-42")


@pytest.mark.asyncio
async def test_gateway_router_search_forwards_tenant_and_project():
    mock_engine = AsyncMock()
    mock_engine.search.return_value = []

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(
        intent=GatewayIntent.SEARCH,
        project="proj-a",
        tenant_id="tenant-7",
        payload={"query": "cache", "top_k": 8},
    )

    resp = await router.handle(req)

    assert resp.ok is True
    mock_engine.search.assert_called_once_with(
        query="cache",
        tenant_id="tenant-7",
        top_k=8,
        project="proj-a",
    )


@pytest.mark.asyncio
async def test_gateway_router_logs_boundary_persist_failure(monkeypatch, caplog):
    mock_engine = AsyncMock()

    class _BoomBoundary:
        def __init__(self, *args, **kwargs):
            pass

        async def _persist(self, exc):
            raise RuntimeError("persist failed")

    monkeypatch.setattr(
        "cortex.extensions.immune.error_boundary.ErrorBoundary",
        _BoomBoundary,
        raising=False,
    )
    mock_engine.search.side_effect = ValueError("Mocked DB failure")

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.SEARCH, payload={"query": "test query"})

    with caplog.at_level("WARNING"):
        resp = await router.handle(req)

    assert resp.ok is False
    assert "Mocked DB failure" in resp.error
    assert any("failed to persist error boundary" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_gateway_router_gidatu_routes_to_handler(monkeypatch):
    mock_engine = AsyncMock()
    handler_mock = AsyncMock(return_value={"status": "ready", "provider": "gidatu"})

    class _FakeGidatuHandler:
        async def handle(self, req):
            return await handler_mock(req)

    monkeypatch.setattr("cortex.gateway.handlers.gidatu.GidatuHandler", _FakeGidatuHandler)

    router = GatewayRouter(engine=mock_engine)
    req = GatewayRequest(intent=GatewayIntent.GIDATU, payload={"action": "status"})

    resp = await router.handle(req)

    assert resp.ok is True
    assert resp.data == {"status": "ready", "provider": "gidatu"}
    handler_mock.assert_awaited_once()
