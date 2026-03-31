from __future__ import annotations

import json
import math
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.engine.postgres_primary import PostgresPrimaryEngine
from cortex.routes.facts import router as facts_router
from cortex.routes.ledger import router as ledger_router
from cortex.routes.memories import router as memories_router
from cortex.routes.search import router as search_router


class _FakeEmbedder:
    def __init__(self, mapping: dict[str, list[float]] | None = None) -> None:
        self.mapping = mapping or {}

    def embed(self, text: str) -> list[float]:
        return list(self.mapping.get(text, [0.1, 0.1, 0.1]))


class _FakeTransaction:
    async def __aenter__(self) -> _FakeTransaction:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _FakeConnection:
    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction()


class _FakePostgresBackend:
    def __init__(self) -> None:
        self.transactions: list[dict[str, Any]] = []
        self.facts: list[dict[str, Any]] = []
        self.merkle_roots: list[dict[str, Any]] = []
        self.agents: list[dict[str, Any]] = []
        self.consensus_votes: list[dict[str, Any]] = []
        self.vote_ledger: list[dict[str, Any]] = []
        self.vote_merkle_roots: list[dict[str, Any]] = []

    @asynccontextmanager
    async def connection(self):
        yield _FakeConnection()

    async def fetchrow_with_conn(
        self,
        conn: Any,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        del conn
        if sql.startswith("SELECT hash FROM transactions"):
            tenant_id = str(params[0])
            rows = [row for row in self.transactions if row["tenant_id"] == tenant_id]
            return {"hash": rows[-1]["hash"]} if rows else None

        if sql.startswith("SELECT id, tenant_id, project FROM facts"):
            fact_id = int(params[0])
            for row in self.facts:
                if int(row["id"]) == fact_id:
                    return {
                        "id": row["id"],
                        "tenant_id": row["tenant_id"],
                        "project": row["project"],
                    }
            return None

        if sql.startswith("SELECT reputation_score FROM agents"):
            agent_id = str(params[0])
            tenant_id = str(params[1])
            for row in self.agents:
                if row["id"] == agent_id and row["tenant_id"] == tenant_id:
                    return {"reputation_score": row["reputation_score"]}
            return None

        if sql.startswith("SELECT hash FROM vote_ledger"):
            tenant_id = str(params[0])
            rows = [row for row in self.vote_ledger if row["tenant_id"] == tenant_id]
            return {"hash": rows[-1]["hash"]} if rows else None

        raise AssertionError(f"Unexpected fetchrow SQL: {sql}")

    async def fetch_with_conn(
        self,
        conn: Any,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        del conn
        return await self.execute(sql, params)

    async def execute_with_conn(
        self,
        conn: Any,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> None:
        del conn
        if sql.startswith("INSERT INTO agents"):
            agent_id = str(params[0])
            if not any(agent["id"] == agent_id for agent in self.agents):
                self.agents.append(
                    {
                        "id": agent_id,
                        "public_key": "",
                        "name": str(params[1]),
                        "agent_type": str(params[2]),
                        "tenant_id": str(params[3]),
                        "reputation_score": float(params[4]),
                        "is_active": True,
                    }
                )
            return

        if sql.startswith("DELETE FROM consensus_votes_v2"):
            fact_id = int(params[0])
            agent_id = str(params[1])
            self.consensus_votes = [
                row
                for row in self.consensus_votes
                if not (int(row["fact_id"]) == fact_id and row["agent_id"] == agent_id)
            ]
            return

        if sql.startswith("UPDATE facts SET consensus_score"):
            fact_id = int(params[3])
            tenant_id = str(params[4])
            for row in self.facts:
                if int(row["id"]) == fact_id and row["tenant_id"] == tenant_id:
                    row["consensus_score"] = float(params[0])
                    row["confidence"] = str(params[1])
                    row["updated_at"] = str(params[2])
                    return
            raise AssertionError(f"Fact #{fact_id} not found for UPDATE")

        if sql.startswith("SELECT set_config"):
            return

        raise AssertionError(f"Unexpected execute SQL: {sql}")

    async def execute_insert_with_conn(
        self,
        conn: Any,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> int:
        del conn
        if sql.startswith("INSERT INTO transactions"):
            tx_id = len(self.transactions) + 1
            self.transactions.append(
                {
                    "id": tx_id,
                    "tenant_id": str(params[0]),
                    "project": str(params[1]),
                    "action": str(params[2]),
                    "detail": str(params[3]),
                    "prev_hash": str(params[4]),
                    "hash": str(params[5]),
                    "timestamp": str(params[6]),
                }
            )
            return tx_id

        if sql.startswith("INSERT INTO facts"):
            fact_id = len(self.facts) + 1
            meta_value = json.loads(str(params[9])) if params[9] else {}
            embedding: list[float] | None = None
            if "embedding" in sql:
                embedding = json.loads(str(params[15]))
            self.facts.append(
                {
                    "id": fact_id,
                    "tenant_id": str(params[0]),
                    "project": str(params[1]),
                    "content": str(params[2]),
                    "fact_type": str(params[3]),
                    "tags": str(params[4]),
                    "confidence": str(params[5]),
                    "valid_from": str(params[6]),
                    "valid_until": params[7],
                    "source": params[8],
                    "meta": meta_value,
                    "consensus_score": float(params[10]),
                    "hash": str(params[11]),
                    "created_at": str(params[12]),
                    "updated_at": str(params[13]),
                    "tx_id": int(params[14]),
                    "embedding": embedding,
                    "is_tombstoned": False,
                    "is_quarantined": False,
                    "quarantined_at": None,
                    "quarantine_reason": None,
                    "tombstoned_at": None,
                }
            )
            return fact_id

        if sql.startswith("INSERT INTO merkle_roots"):
            checkpoint_id = len(self.merkle_roots) + 1
            self.merkle_roots.append(
                {
                    "id": checkpoint_id,
                    "tenant_id": str(params[0]),
                    "root_hash": str(params[1]),
                    "tx_start_id": int(params[2]),
                    "tx_end_id": int(params[3]),
                    "tx_count": int(params[4]),
                }
            )
            return checkpoint_id

        if sql.startswith("INSERT INTO consensus_votes_v2"):
            fact_id = int(params[0])
            agent_id = str(params[1])
            existing = next(
                (
                    row
                    for row in self.consensus_votes
                    if int(row["fact_id"]) == fact_id and row["agent_id"] == agent_id
                ),
                None,
            )
            vote_id = int(existing["id"]) if existing is not None else len(self.consensus_votes) + 1
            payload = {
                "id": vote_id,
                "fact_id": fact_id,
                "agent_id": agent_id,
                "vote": int(params[2]),
                "vote_weight": float(params[3]),
                "agent_rep_at_vote": float(params[4]),
                "stake_at_vote": float(params[5]),
                "created_at": str(params[6]),
                "decay_factor": float(params[7]),
                "vote_reason": params[8],
                "meta": json.loads(str(params[9])) if params[9] else {},
                "tx_id": int(params[10]) if len(params) > 10 and params[10] is not None else None,
            }
            if existing is None:
                self.consensus_votes.append(payload)
            else:
                existing.update(payload)
            return vote_id

        if sql.startswith("INSERT INTO vote_ledger"):
            vote_id = len(self.vote_ledger) + 1
            self.vote_ledger.append(
                {
                    "id": vote_id,
                    "tenant_id": str(params[0]),
                    "fact_id": int(params[1]),
                    "agent_id": str(params[2]),
                    "vote": int(params[3]),
                    "vote_weight": float(params[4]),
                    "prev_hash": str(params[5]),
                    "hash": str(params[6]),
                    "timestamp": str(params[7]),
                    "signature": params[8],
                    "tx_id": int(params[9]) if params[9] is not None else None,
                }
            )
            return vote_id

        if sql.startswith("INSERT INTO vote_merkle_roots"):
            checkpoint_id = len(self.vote_merkle_roots) + 1
            self.vote_merkle_roots.append(
                {
                    "id": checkpoint_id,
                    "tenant_id": str(params[0]),
                    "root_hash": str(params[1]),
                    "vote_start_id": int(params[2]),
                    "vote_end_id": int(params[3]),
                    "vote_count": int(params[4]),
                }
            )
            return checkpoint_id

        raise AssertionError(f"Unexpected INSERT SQL: {sql}")

    async def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        if sql.startswith("SELECT id FROM facts"):
            tenant_id, project, fact_hash = str(params[0]), str(params[1]), str(params[2])
            for row in self.facts:
                if (
                    row["tenant_id"] == tenant_id
                    and row["project"] == project
                    and row["hash"] == fact_hash
                    and not row["is_tombstoned"]
                    and not row["is_quarantined"]
                    and row["valid_until"] is None
                ):
                    return [{"id": row["id"]}]
            return []

        if "FROM transactions" in sql:
            tenant_id = str(params[0])
            rows = [row for row in self.transactions if row["tenant_id"] == tenant_id]
            if "id > ?" in sql:
                rows = [row for row in rows if int(row["id"]) > int(params[1])]
            if "id >= ?" in sql and "id <= ?" in sql:
                rows = [
                    row
                    for row in rows
                    if int(params[1]) <= int(row["id"]) <= int(params[2])
                ]
            return [dict(row) for row in sorted(rows, key=lambda row: int(row["id"]))]

        if "FROM merkle_roots" in sql:
            tenant_id = str(params[0])
            rows = [row for row in self.merkle_roots if row["tenant_id"] == tenant_id]
            if "MAX(tx_end_id)" in sql:
                if not rows:
                    return [{"max_tx": None}]
                return [{"max_tx": max(int(row["tx_end_id"]) for row in rows)}]
            return [dict(row) for row in sorted(rows, key=lambda row: int(row["id"]))]

        if "FROM vote_ledger" in sql:
            tenant_id = str(params[0])
            rows = [row for row in self.vote_ledger if row["tenant_id"] == tenant_id]
            if "id > COALESCE((" in sql:
                covered = 0
                roots = [row for row in self.vote_merkle_roots if row["tenant_id"] == tenant_id]
                if roots:
                    covered = max(int(row["vote_end_id"]) for row in roots)
                rows = [row for row in rows if int(row["id"]) > covered]
            if "id >= ?" in sql and "id <= ?" in sql:
                rows = [
                    row
                    for row in rows
                    if int(params[1]) <= int(row["id"]) <= int(params[2])
                ]
            if "LIMIT ?" in sql:
                rows = rows[: int(params[-1])]
            return [dict(row) for row in sorted(rows, key=lambda row: int(row["id"]))]

        if "FROM vote_merkle_roots" in sql:
            tenant_id = str(params[0])
            rows = [row for row in self.vote_merkle_roots if row["tenant_id"] == tenant_id]
            return [dict(row) for row in sorted(rows, key=lambda row: int(row["id"]))]

        if "FROM consensus_votes_v2 v " in sql and "JOIN agents a" in sql:
            fact_id = int(params[0])
            tenant_id = str(params[1])
            rows: list[dict[str, Any]] = []
            for vote in self.consensus_votes:
                if int(vote["fact_id"]) != fact_id:
                    continue
                agent = next(
                    (
                        row
                        for row in self.agents
                        if row["id"] == vote["agent_id"]
                        and row["tenant_id"] == tenant_id
                        and row.get("is_active", True)
                    ),
                    None,
                )
                if agent is None:
                    continue
                rows.append(
                    {
                        "vote": vote["vote"],
                        "vote_weight": vote["vote_weight"],
                        "reputation_score": agent["reputation_score"],
                    }
                )
            return rows

        if sql.startswith("SELECT agent_id, vote, tx_id FROM consensus_votes_v2"):
            fact_id = int(params[0])
            rows = [
                row
                for row in self.consensus_votes
                if int(row["fact_id"]) == fact_id
            ]
            return [dict(row) for row in sorted(rows, key=lambda row: int(row["id"]))]

        if "FROM facts" in sql:
            if "embedding <=>" in sql:
                query_embedding = json.loads(str(params[0]))
                tenant_id = str(params[1])
                param_index = 2
                rows = [
                    row
                    for row in self.facts
                    if row["tenant_id"] == tenant_id
                    and not row["is_tombstoned"]
                    and not row["is_quarantined"]
                    and row.get("embedding") is not None
                ]
                if " AND project = ?" in sql:
                    project = str(params[param_index])
                    rows = [row for row in rows if row["project"] == project]
                limit = int(params[-1])
                ranked: list[dict[str, Any]] = []
                for row in rows:
                    enriched = dict(row)
                    enriched["score"] = _cosine_similarity(query_embedding, row["embedding"])
                    ranked.append(enriched)
                ranked.sort(key=lambda row: float(row["score"]), reverse=True)
                return ranked[:limit]

            rows = list(self.facts)
            param_index = 0
            if "tenant_id = ?" in sql:
                tenant_id = str(params[param_index])
                rows = [row for row in rows if row["tenant_id"] == tenant_id]
                param_index += 1
            if "project = ?" in sql:
                project = str(params[param_index])
                rows = [row for row in rows if row["project"] == project]
                param_index += 1
            if " AND id = ?" in sql:
                fact_id = int(params[param_index])
                rows = [row for row in rows if int(row["id"]) == fact_id]
                param_index += 1
            if "is_tombstoned = FALSE" in sql:
                rows = [row for row in rows if not row["is_tombstoned"]]
            if "is_quarantined = FALSE" in sql:
                rows = [row for row in rows if not row["is_quarantined"]]
            rows.sort(key=lambda row: str(row["created_at"]), reverse=True)
            if "LIMIT ?" in sql:
                limit = int(params[-1])
                rows = rows[:limit]
            return [dict(row) for row in rows]

        raise AssertionError(f"Unexpected SELECT SQL: {sql}")


class _NoVectorSearchBackend(_FakePostgresBackend):
    async def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        if "embedding <=>" in sql:
            raise RuntimeError("pgvector operator unavailable")
        return await super().execute(sql, params)


def _cosine_similarity(left: list[float], right: list[float] | None) -> float:
    if right is None:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _build_client(
    backend: _FakePostgresBackend | None = None,
    embedder: _FakeEmbedder | None = None,
) -> TestClient:
    app = FastAPI()
    app.state.primary_async_engine = PostgresPrimaryEngine(
        backend or _FakePostgresBackend(),
        embedder=embedder,
    )
    app.state.async_engine = None
    app.include_router(facts_router)
    app.include_router(memories_router)
    app.include_router(ledger_router)
    app.include_router(search_router)
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-pg",
        role="admin",
        permissions=["read", "write", "admin"],
        key_name="test-admin",
    )
    return TestClient(app)


def test_postgres_primary_engine_drives_store_ledger_and_query_api_path() -> None:
    client = _build_client(
        embedder=_FakeEmbedder(
            {
                "PostgreSQL primary path proof for the public API": [1.0, 0.0, 0.0],
                "query routed through semantic vector ranking": [0.0, 1.0, 0.0],
                "checkpoint semantics without lexical overlap": [0.0, 1.0, 0.0],
            }
        )
    )

    store_response = client.post(
        "/v1/memories",
        json={
            "project": "pg-demo",
            "content": "PostgreSQL primary path proof for the public API",
            "type": "knowledge",
            "tags": ["postgres", "proof"],
            "source": "api-test",
            "metadata": {"vertical": "store-ledger-query"},
        },
    )
    assert store_response.status_code == 200
    assert store_response.json() == {"id": 1, "project": "pg-demo", "status": "stored"}

    second_store_response = client.post(
        "/v1/memories",
        json={
            "project": "pg-demo",
            "content": "query routed through semantic vector ranking",
            "type": "knowledge",
            "tags": ["postgres", "vector"],
            "source": "api-test",
            "metadata": {"vertical": "store-ledger-query"},
        },
    )
    assert second_store_response.status_code == 200
    assert second_store_response.json() == {"id": 2, "project": "pg-demo", "status": "stored"}

    query_response = client.post(
        "/v1/search",
        json={"query": "checkpoint semantics without lexical overlap", "k": 3, "project": "pg-demo"},
    )
    assert query_response.status_code == 200
    search_payload = query_response.json()
    assert len(search_payload) >= 1
    assert search_payload[0]["fact_id"] == 2
    assert search_payload[0]["project"] == "pg-demo"
    assert search_payload[0]["content"] == "query routed through semantic vector ranking"
    assert search_payload[0]["hash"]

    vote_response = client.post("/v1/facts/1/vote", json={"value": 1})
    assert vote_response.status_code == 200
    assert vote_response.json() == {
        "fact_id": 1,
        "agent": "test-admin",
        "vote": 1,
        "new_consensus_score": 2.0,
        "confidence": "verified",
        "status": "recorded",
    }

    votes_response = client.get("/v1/facts/1/votes")
    assert votes_response.status_code == 200
    assert votes_response.json() == [{"agent": "test-admin", "vote": 1, "tx_id": 3}]

    recall_response = client.get("/v1/memories", params={"project": "pg-demo"})
    assert recall_response.status_code == 200
    recall_payload = recall_response.json()
    assert len(recall_payload) == 2
    assert {item["id"] for item in recall_payload} == {1, 2}
    assert all(item["project"] == "pg-demo" for item in recall_payload)
    recall_by_id = {item["id"]: item for item in recall_payload}
    assert recall_by_id[1]["content"] == "PostgreSQL primary path proof for the public API"
    assert recall_by_id[1]["tags"] == ["postgres", "proof"]
    assert recall_by_id[2]["content"] == "query routed through semantic vector ranking"
    assert recall_by_id[2]["tags"] == ["postgres", "vector"]

    checkpoint_response = client.post("/v1/ledger/checkpoint")
    assert checkpoint_response.status_code == 200
    assert checkpoint_response.json() == {
        "checkpoint_id": 1,
        "checkpoint_ref": "#1",
        "vote_checkpoint_id": 1,
        "vote_checkpoint_ref": "#1",
        "message": "Merkle checkpoints created successfully (tx #1, vote #1)",
        "status": "success",
    }

    ledger_response = client.get("/v1/ledger/status")
    if ledger_response.status_code != 200 or not ledger_response.json().get("valid"):
        print(f"DEBUG: Ledger status response: {ledger_response.json()}")

    assert ledger_response.status_code == 200
    assert ledger_response.json() == {
        "valid": True,
        "violations": [],
        "tx_checked": 3,
        "roots_checked": 1,
        "votes_checked": 1,
        "vote_checkpoints_checked": 1,
    }


def test_postgres_primary_search_falls_back_to_scan_when_vector_query_is_unavailable() -> None:
    client = _build_client(
        backend=_NoVectorSearchBackend(),
        embedder=_FakeEmbedder({"fallback lexical match": [1.0, 0.0, 0.0]}),
    )

    store_response = client.post(
        "/v1/memories",
        json={
            "project": "pg-fallback",
            "content": "fallback lexical match",
            "type": "knowledge",
            "tags": ["postgres"],
        },
    )
    assert store_response.status_code == 200

    query_response = client.post(
        "/v1/search",
        json={"query": "fallback lexical", "k": 3, "project": "pg-fallback"},
    )
    assert query_response.status_code == 200
    search_payload = query_response.json()
    assert len(search_payload) == 1
    assert search_payload[0]["fact_id"] == 1
    assert search_payload[0]["content"] == "fallback lexical match"
