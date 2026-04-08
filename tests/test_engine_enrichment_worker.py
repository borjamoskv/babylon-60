from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from cortex.engine.enrichment_worker import process_next_job


@pytest.mark.asyncio
async def test_process_next_job_accepts_pending_status(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "engine_enrichment.db"

    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                project TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                semantic_status TEXT DEFAULT 'pending',
                semantic_error TEXT
            );
            CREATE TABLE enrichment_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            );
            """
        )
        await conn.execute(
            "INSERT INTO facts (id, content, project, tenant_id) VALUES (1, 'hello', 'proj', 'tenant')"
        )
        await conn.execute(
            "INSERT INTO enrichment_jobs (fact_id, status) VALUES (1, 'pending')"
        )
        await conn.commit()

    class _Engine:
        def __init__(self, path: str) -> None:
            self._path = path
            self.embeddings = SimpleNamespace(enrich_fact=AsyncMock())

        def session(self):
            return aiosqlite.connect(self._path)

    caps = SimpleNamespace(embeddings=True)
    monkeypatch.setattr(
        "cortex.engine.enrichment_worker.CapabilityRegistry.get_instance",
        lambda: SimpleNamespace(capabilities=caps),
    )

    engine = _Engine(str(db_path))
    processed = await process_next_job(engine)

    assert processed is True
    engine.embeddings.enrich_fact.assert_awaited_once_with(1, "hello", "proj", "tenant")

    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT semantic_status FROM facts WHERE id = 1") as cursor:
            fact_row = await cursor.fetchone()
        async with conn.execute("SELECT COUNT(*) FROM enrichment_jobs WHERE fact_id = 1") as cursor:
            job_row = await cursor.fetchone()

    assert fact_row is not None
    assert fact_row[0] == "indexed"
    assert job_row is not None
    assert job_row[0] == 0
