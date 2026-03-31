from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.gateway import GatewayResponse
from cortex.gateway.adapters import rest


class StubGateway:
    def __init__(self) -> None:
        self.requests = []

    async def handle(self, request):
        self.requests.append(request)
        return GatewayResponse(
            ok=True,
            data={"echo_tenant": request.tenant_id},
            intent=request.intent,
            request_id=request.request_id,
            latency_ms=1.0,
        )


def _build_client(gateway: StubGateway, auth_result: AuthResult | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(rest.router)
    app.dependency_overrides[rest._get_router] = lambda: gateway
    if auth_result is not None:
        app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def test_gateway_status_requires_auth():
    gateway = StubGateway()
    client = _build_client(gateway)

    response = client.get("/gateway/v1/status")

    assert response.status_code == 401
    assert gateway.requests == []


def test_gateway_search_propagates_tenant_and_caller():
    gateway = StubGateway()
    client = _build_client(
        gateway,
        AuthResult(
            authenticated=True,
            tenant_id="tenant-red",
            permissions=["read", "write"],
            key_name="edge-key",
        ),
    )

    response = client.post(
        "/gateway/v1/search",
        json={"query": "ledger", "project": "alpha", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["data"]["echo_tenant"] == "tenant-red"
    assert len(gateway.requests) == 1
    request = gateway.requests[0]
    assert request.tenant_id == "tenant-red"
    assert request.caller_id == "edge-key"
    assert request.project == "alpha"
    assert request.payload == {"query": "ledger", "top_k": 3}


def test_gateway_recall_keeps_tenant_scope():
    gateway = StubGateway()
    client = _build_client(
        gateway,
        AuthResult(
            authenticated=True,
            tenant_id="tenant-blue",
            permissions=["read"],
            key_name="reader-key",
        ),
    )

    response = client.post("/gateway/v1/recall", json={"project": "ops"})

    assert response.status_code == 200
    assert len(gateway.requests) == 1
    request = gateway.requests[0]
    assert request.tenant_id == "tenant-blue"
    assert request.project == "ops"
