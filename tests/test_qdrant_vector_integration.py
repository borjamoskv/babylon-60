from __future__ import annotations

import aiosqlite
import pytest

from cortex.engine.embedding_engine import embed_fact_async
from cortex.search.vector import semantic_search


class FakeVectorBackend:
    def __init__(self, hits: list[tuple[int, float]] | None = None) -> None:
        self.hits = hits or []
        self.search_calls: list[dict[str, object]] = []
        self.upsert_calls: list[dict[str, object]] = []

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[tuple[int, float]]:
        self.search_calls.append(
            {
                "query_embedding": query_embedding,
                "top_k": top_k,
                "tenant_id": tenant_id,
                "project": project,
            }
        )
        return self.hits

    async def upsert(
        self,
        fact_id: int,
        embedding: list[float],
        tenant_id: str = "default",
        payload: dict[str, object] | None = None,
    ) -> None:
        self.upsert_calls.append(
            {
                "fact_id": fact_id,
                "embedding": embedding,
                "tenant_id": tenant_id,
                "payload": payload or {},
            }
        )


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        assert text
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_semantic_search_uses_qdrant_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = FakeVectorBackend(hits=[(2, 0.91), (1, 0.77)])
    monkeypatch.setattr("cortex.search.vector.get_vector_backend", lambda: backend)

    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                content TEXT,
                project TEXT,
                fact_type TEXT,
                confidence TEXT,
                valid_from TEXT,
                valid_until TEXT,
                tags TEXT,
                source TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT,
                tx_id INTEGER,
                hash TEXT
            )
            """
        )
        await conn.executemany(
            """
            INSERT INTO facts (
                id, tenant_id, content, project, fact_type, confidence,
                valid_from, valid_until, tags, source, metadata,
                created_at, updated_at, tx_id, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "tenant-a",
                    "first fact",
                    "proj",
                    "knowledge",
                    "stated",
                    "2026-01-01T00:00:00Z",
                    None,
                    "[]",
                    "test",
                    "{}",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                    11,
                    "hash-1",
                ),
                (
                    2,
                    "tenant-a",
                    "second fact",
                    "proj",
                    "knowledge",
                    "stated",
                    "2026-01-02T00:00:00Z",
                    None,
                    "[]",
                    "test",
                    "{}",
                    "2026-01-02T00:00:00Z",
                    "2026-01-02T00:00:00Z",
                    12,
                    "hash-2",
                ),
            ],
        )
        await conn.commit()

        results = await semantic_search(
            conn,
            [0.1, 0.2, 0.3],
            top_k=2,
            tenant_id="tenant-a",
            project="proj",
        )

    assert [result.fact_id for result in results] == [2, 1]
    assert results[0].score == pytest.approx(0.91)
    assert results[1].score == pytest.approx(0.77)
    assert backend.search_calls[0]["project"] == "proj"


@pytest.mark.asyncio
async def test_embed_fact_async_dual_writes_qdrant(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = FakeVectorBackend()
    monkeypatch.setattr("cortex.engine.embedding_engine.get_vector_backend", lambda: backend)

    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute("CREATE TABLE fact_embeddings (fact_id INTEGER, embedding TEXT)")

        await embed_fact_async(
            conn=conn,
            fact_id=42,
            project="proj",
            content="hello cloud vectors",
            embedder=FakeEmbedder(),
            tenant_id="tenant-a",
        )

        cursor = await conn.execute("SELECT fact_id, embedding FROM fact_embeddings")
        rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == 42
    assert backend.upsert_calls == [
        {
            "fact_id": 42,
            "embedding": [0.1, 0.2, 0.3],
            "tenant_id": "tenant-a",
            "payload": {"project": "proj"},
        }
    ]
