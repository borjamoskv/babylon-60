from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import aiosqlite
import pytest

from cortex.engine.store_mutation import purge_logic


class _PurgeEngine:
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn
        self.logged: list[dict[str, Any]] = []

    @asynccontextmanager
    async def session(self):
        yield self._conn

    async def _log_transaction(
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        detail: dict[str, Any],
        tenant_id: str,
    ) -> int:
        self.logged.append(
            {"project": project, "action": action, "detail": detail, "tenant_id": tenant_id}
        )
        return 1


@pytest.mark.asyncio
async def test_purge_scopes_fts_side_effect_by_tenant_when_supported():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER,
                tenant_id TEXT NOT NULL,
                fact_type TEXT,
                valid_until TEXT,
                is_tombstoned INTEGER,
                is_quarantined INTEGER
            )
            """
        )
        await conn.execute("CREATE TABLE facts_fts (rowid INTEGER, tenant_id TEXT, content TEXT)")
        await conn.execute(
            """
            INSERT INTO facts
                (id, tenant_id, fact_type, valid_until, is_tombstoned, is_quarantined)
            VALUES (1, 'tenant-a', 'knowledge', NULL, 0, 0)
            """
        )
        await conn.executemany(
            "INSERT INTO facts_fts (rowid, tenant_id, content) VALUES (?, ?, ?)",
            [
                (1, "tenant-a", "tenant a indexed content"),
                (1, "tenant-b", "tenant b indexed content"),
            ],
        )
        await conn.commit()

        engine = _PurgeEngine(conn)
        purged = await purge_logic(
            mixin_instance=engine,
            fact_id=1,
            tenant_id="tenant-a",
            force=True,
        )

        remaining_fts = await (
            await conn.execute("SELECT tenant_id, content FROM facts_fts ORDER BY tenant_id")
        ).fetchall()
        remaining_facts = await (await conn.execute("SELECT COUNT(*) FROM facts")).fetchone()

    assert purged is True
    assert engine.logged[0]["action"] == "purge"
    assert engine.logged[0]["tenant_id"] == "tenant-a"
    assert remaining_fts == [("tenant-b", "tenant b indexed content")]
    assert remaining_facts[0] == 0
