import pytest
import logging
import aiosqlite
import sqlite3
from cortex.guards.contradiction_guard.batch import scan_all_contradictions
import contextlib

pytestmark = pytest.mark.asyncio

async def test_scan_all_contradictions_happy_path(fts5_db_path, caplog):
    """Happy Path: scan over database returns correct pairs."""
    async with aiosqlite.connect(fts5_db_path) as db:
        await db.execute("""
            INSERT INTO facts (project, content, fact_type, created_at)
            VALUES
            ('projC', 'We adopt MongoDB as our primary DB.', 'decision', '2023-11-01'),
            ('projC', 'We adopt MongoDB and never use Postgres.', 'decision', '2023-11-02')
        """)
        await db.commit()

    with caplog.at_level(logging.WARNING):
        pairs = await scan_all_contradictions(db_path=fts5_db_path, min_score=0.1)

    found = any(p[0].project == "projC" and p[1].project == "projC" for p in pairs)
    assert found
    assert "Batch contradiction scan failed" not in caplog.text

async def test_scan_all_contradictions_rejection(fts5_db_path, caplog, monkeypatch):
    """Rejection/Warning test: Handle database failure properly."""
    async def mock_execute(*args, **kwargs):
        raise aiosqlite.OperationalError("Mocked DB error")

    @contextlib.asynccontextmanager
    async def mock_connect(*args, **kwargs):
        class MockConn:
            row_factory = None
            async def execute(self, *a, **k):
                return await mock_execute(*a, **k)
        yield MockConn()

    monkeypatch.setattr("cortex.guards.contradiction_guard.batch.connect_async_ctx", mock_connect)

    with caplog.at_level(logging.WARNING):
        pairs = await scan_all_contradictions(db_path=fts5_db_path, min_score=0.1)

    assert pairs == []
    assert "Batch contradiction scan failed" in caplog.text

async def test_scan_all_contradictions_boundary(fts5_db_path, caplog):
    """Boundary Condition: Small limit returns exact number of elements."""
    async with aiosqlite.connect(fts5_db_path) as db:
        for i in range(10):
            await db.execute(
                "INSERT INTO facts (project, content, fact_type, created_at) VALUES (?, ?, ?, ?)",
                ('projLimit', f'We must adopt Docker for deployment {i}', 'decision', '2023-11-01')
            )
        await db.commit()

    with caplog.at_level(logging.WARNING):
        pairs = await scan_all_contradictions(db_path=fts5_db_path, min_score=0.1, limit=2)

    assert len(pairs) == 2
    assert "Batch contradiction scan failed" not in caplog.text
