from __future__ import annotations

import os
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.engine.postgres_primary import PostgresPrimaryEngine
from cortex.routes.facts import router as facts_router
from cortex.routes.ledger import router as ledger_router
from cortex.routes.memories import router as memories_router
from cortex.routes.search import router as search_router
from cortex.storage.env import get_postgres_dsn
from cortex.storage.postgres import PostgresBackend

_TEST_POSTGRES_DSN = os.environ.get("CORTEX_TEST_POSTGRES_DSN") or get_postgres_dsn()

pytestmark = pytest.mark.skipif(
    not _TEST_POSTGRES_DSN,
    reason=(
        "Set CORTEX_TEST_POSTGRES_DSN or a supported PostgreSQL DSN alias "
        "(POSTGRES_DSN, CORTEX_PG_DSN, CORTEX_PG_URL, DATABASE_URL, PG_URL) "
        "to run real PostgreSQL integration tests."
    ),
)


@pytest.mark.asyncio
async def test_postgres_primary_api_path_against_real_backend() -> None:
    """Exercise the public API vertical slice against a real PostgreSQL backend."""
    assert _TEST_POSTGRES_DSN is not None

    backend = PostgresBackend(
        dsn=_TEST_POSTGRES_DSN,
        min_size=1,
        max_size=1,
        auto_init_schema=True,
    )
    await backend.connect()

    tenant_id = f"tenant-pg-it-{uuid.uuid4().hex[:8]}"
    project = f"pg-it-{uuid.uuid4().hex[:8]}"

    app = FastAPI()
    app.state.primary_async_engine = PostgresPrimaryEngine(backend=backend)
    app.state.async_engine = None
    app.include_router(facts_router)
    app.include_router(memories_router)
    app.include_router(ledger_router)
    app.include_router(search_router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id=tenant_id,
        role="admin",
        permissions=["read", "write", "admin"],
        key_name="integration-admin",
    )

    try:
        with TestClient(app) as client:
            store_response = client.post(
                "/v1/memories",
                json={
                    "project": project,
                    "content": "PostgreSQL integration proof through the public API path",
                    "type": "knowledge",
                    "tags": ["postgres", "integration"],
                    "source": "integration-test",
                    "metadata": {"vertical": "store-ledger-query", "kind": "integration"},
                },
            )
            assert store_response.status_code == 200, store_response.text
            stored_id = store_response.json()["id"]

            search_response = client.post(
                "/v1/search",
                json={"query": "integration proof public API", "k": 3, "project": project},
            )
            assert search_response.status_code == 200, search_response.text
            search_payload = search_response.json()
            assert len(search_payload) >= 1
            assert search_payload[0]["fact_id"] == stored_id
            assert search_payload[0]["project"] == project
            assert search_payload[0]["content"] == (
                "PostgreSQL integration proof through the public API path"
            )

            recall_response = client.get("/v1/memories", params={"project": project})
            assert recall_response.status_code == 200, recall_response.text
            recall_payload = recall_response.json()
            assert len(recall_payload) >= 1
            assert recall_payload[0]["id"] == stored_id
            assert recall_payload[0]["project"] == project
            assert recall_payload[0]["content"] == (
                "PostgreSQL integration proof through the public API path"
            )
            assert recall_payload[0]["tags"] == ["postgres", "integration"]

            vote_response = client.post(f"/v1/facts/{stored_id}/vote", json={"value": 1})
            assert vote_response.status_code == 200, vote_response.text
            vote_payload = vote_response.json()
            assert vote_payload["fact_id"] == stored_id
            assert vote_payload["vote"] == 1
            assert vote_payload["new_consensus_score"] >= 1.0

            checkpoint_response = client.post("/v1/ledger/checkpoint")
            assert checkpoint_response.status_code == 200, checkpoint_response.text
            checkpoint_payload = checkpoint_response.json()
            assert checkpoint_payload["checkpoint_id"] is not None
            assert checkpoint_payload["vote_checkpoint_id"] is not None

            ledger_response = client.get("/v1/ledger/status")
            assert ledger_response.status_code == 200, ledger_response.text
            ledger_payload = ledger_response.json()
            if not ledger_payload["valid"]:
                print(f"DEBUG LEDGER: {ledger_payload}")
            assert ledger_payload["valid"] is True
            assert ledger_payload["tx_checked"] >= 2
            assert ledger_payload["roots_checked"] >= 1
            assert ledger_payload["votes_checked"] >= 1
            assert ledger_payload["vote_checkpoints_checked"] >= 1
    finally:
        await backend.close()
