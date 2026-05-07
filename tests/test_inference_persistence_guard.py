from __future__ import annotations

import aiosqlite
import pytest

from cortex.engine.inference import InferenceEngine


@pytest.mark.asyncio
async def test_inference_persistence_requires_canonical_store_callback() -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        await conn.executescript(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                project TEXT NOT NULL,
                confidence TEXT,
                tenant_id TEXT NOT NULL,
                valid_until TEXT,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            INSERT INTO facts (content, fact_type, project, confidence, tenant_id, valid_until)
            VALUES
                ('duplicate source content', 'knowledge', 'proj', 'C5', 'tenant-alpha', NULL),
                ('duplicate source content', 'knowledge', 'proj', 'C5', 'tenant-alpha', NULL);
            """
        )
        await conn.commit()

        engine = InferenceEngine(max_derivations=1)
        with pytest.raises(RuntimeError, match="canonical store_fact"):
            await engine.derive(conn, tenant_id="tenant-alpha")

        cursor = await conn.execute("SELECT COUNT(*) FROM facts")
        assert (await cursor.fetchone())[0] == 2
    finally:
        await conn.close()
