from __future__ import annotations

from types import SimpleNamespace

import aiosqlite
import pytest

from cortex.engine.store_validation import _apply_semantic_dedup


class _FakeL2:
    async def recall(self, query: str, limit: int, project: str, tenant_id: str):
        return [SimpleNamespace(id=1, _recall_score=0.93)]


class _FakeManager:
    _l2 = _FakeL2()


class _FakeMixin:
    _thermal_decay_cache: dict[int, int] = {}
    _memory_manager = _FakeManager()

    async def deprecate(self, *args, **kwargs):
        raise AssertionError("deprecate should not be called in this test")


@pytest.mark.asyncio
async def test_semantic_dedup_returns_id_even_without_last_accessed_column():
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY)")
    await conn.execute("INSERT INTO facts (id) VALUES (1)")
    await conn.commit()

    mixin = _FakeMixin()
    fid = await _apply_semantic_dedup(mixin, conn, "proj", "content", "tenant-a")

    assert fid == 1
    await conn.close()
