from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cortex.api.deps import get_async_engine
from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.extensions.swarm.psychohistory import AGENT_BIASES
from cortex.routes import swarm as swarm_router
from cortex.utils.result import Ok

TEST_AUTH = AuthResult(
    authenticated=True,
    tenant_id="test-tenant",
    permissions=["read", "write", "admin"],
    key_name="test_key",
)


async def override_auth() -> AuthResult:
    return TEST_AUTH


@pytest.fixture
def mock_engine() -> AsyncMock:
    engine = AsyncMock()
    router = AsyncMock()
    router.execute_resilient.side_effect = lambda prompt: Ok(
        "O(1) Contingency Crystal"
        if "Hari Seldon" in prompt.system_instruction
        else "Simulated cascade effect"
    )
    engine.get_router.return_value = router
    engine.store.return_value = None
    return engine


@pytest.fixture
async def client(mock_engine: AsyncMock) -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    app.include_router(swarm_router.router)
    app.dependency_overrides[get_async_engine] = lambda: mock_engine
    app.dependency_overrides[require_auth] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_psychohistory_simulation_api(
    client: AsyncClient,
    mock_engine: AsyncMock,
) -> None:
    payload = {
        "scenario_name": "Apagón Satelital Test",
        "simulated_years": 10,
        "project": "TEST_PROJECT",
    }

    resp = await client.post("/v1/swarm/psychohistory", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["scenario"] == "Apagón Satelital Test"
    assert data["simulated_years"] == 10
    assert data["active_agents"] == len(AGENT_BIASES)
    assert data["contingency_crystal"] == "O(1) Contingency Crystal"
    assert data["resonance"] > 0

    mock_engine.store.assert_called_once()
    store_kwargs = mock_engine.store.call_args.kwargs
    assert store_kwargs["project"] == "TEST_PROJECT"
    assert store_kwargs["content"] == "O(1) Contingency Crystal"
    assert store_kwargs["fact_type"] == "bridge"
    assert store_kwargs["confidence"] == "C5"
    assert store_kwargs["source"] == "swarm:psychohistory"
    assert store_kwargs["meta"]["scenario"] == "Apagón Satelital Test"
