import pytest
import aiosqlite
import logging
from pathlib import Path

from cortex.guards.contradiction_guard import (
    detect_contradictions,
    scan_all_contradictions,
    ConflictCandidate,
    ConflictReport,
)

@pytest.fixture
async def memory_db():
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            created_at TEXT
        )
        """
    )
    await conn.execute(
        """
        CREATE VIRTUAL TABLE facts_fts USING fts5(content, content='facts', content_rowid='id')
        """
    )

    # Insert some data
    await conn.execute(
        "INSERT INTO facts (project, content, fact_type, created_at) VALUES (?, ?, ?, ?)",
        ("proj_A", "We will use Redis for caching.", "decision", "2024-01-01"),
    )
    await conn.execute(
        "INSERT INTO facts_fts (rowid, content) VALUES (?, ?)",
        (1, "We will use Redis for caching."),
    )

    await conn.execute(
        "INSERT INTO facts (project, content, fact_type, created_at) VALUES (?, ?, ?, ?)",
        ("proj_B", "The user dashboard requires real-time updates.", "decision", "2024-01-02"),
    )
    await conn.execute(
        "INSERT INTO facts_fts (rowid, content) VALUES (?, ?)",
        (2, "The user dashboard requires real-time updates."),
    )

    await conn.execute(
        "INSERT INTO facts (project, content, fact_type, created_at) VALUES (?, ?, ?, ?)",
        ("proj_A", "Redis caching is replaced by Memcached.", "decision", "2024-01-03"),
    )
    await conn.execute(
        "INSERT INTO facts_fts (rowid, content) VALUES (?, ?)",
        (3, "Redis caching is replaced by Memcached."),
    )

    await conn.commit()
    yield conn
    await conn.close()

# In order to mock the context manager, we need a custom fixture
@pytest.fixture
def mock_db_ctx(monkeypatch, memory_db):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_connect(db_path):
        yield memory_db

    monkeypatch.setattr("cortex.guards.contradiction_guard.detector.connect_async_ctx", mock_connect)

# ── Tests for detect_contradictions ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_contradictions_happy_path(mock_db_ctx, caplog):
    """Happy Path: valid input passes without contradiction."""
    caplog.set_level(logging.WARNING)
    report = await detect_contradictions(
        new_content="We are using PostgreSQL for relational data storage.",
        new_project="proj_A",
        db_path=":memory:",
    )
    assert not report.has_conflicts
    assert report.severity == "clean"
    assert "✅ No contradictions detected." in report.format()
    # No warning logs
    assert len(caplog.records) == 0

@pytest.mark.asyncio
async def test_detect_contradictions_rejection_warning(mock_db_ctx, caplog):
    """Rejection/Warning test: invalid input flagged with contradictions."""
    caplog.set_level(logging.WARNING)
    # This should contradict the existing Redis or Memcached decision
    report = await detect_contradictions(
        new_content="We will no longer use Redis, it is prohibited.",
        new_project="proj_A",
        db_path=":memory:",
    )
    assert report.has_conflicts
    assert report.severity in ["medium", "high"]
    assert len(report.candidates) > 0
    formatted = report.format()
    assert "potential contradiction" in formatted

    # We should have candidates
    assert any(c.fact_id == 1 for c in report.candidates)

@pytest.mark.asyncio
async def test_detect_contradictions_boundary_condition(mock_db_ctx, caplog):
    """Boundary Condition test: edge case verification (too short or noise)."""
    caplog.set_level(logging.WARNING)

    # Too short
    report = await detect_contradictions(
        new_content="ok",
        new_project="proj_A",
        db_path=":memory:",
    )
    assert not report.has_conflicts

    # Noise prefix
    report = await detect_contradictions(
        new_content="MAILTV-1: ARCHIVE This is an archived message.",
        new_project="proj_A",
        db_path=":memory:",
    )
    assert not report.has_conflicts

@pytest.mark.asyncio
async def test_detect_contradictions_db_error(monkeypatch, caplog):
    """Boundary Condition test: db error triggers warning and returns clean report."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_connect_error(db_path):
        class MockConn:
            row_factory = None
            async def execute(self, *args, **kwargs):
                raise aiosqlite.OperationalError("Simulated DB Error")
        yield MockConn()

    monkeypatch.setattr("cortex.guards.contradiction_guard.detector.connect_async_ctx", mock_connect_error)

    caplog.set_level(logging.WARNING)
    report = await detect_contradictions(
        new_content="We will use Redis for caching.",
        new_project="proj_A",
        db_path=":memory:",
    )

    assert not report.has_conflicts
    assert any("Contradiction scan failed (DB error)" in record.message for record in caplog.records)


# ── Tests for scan_all_contradictions ────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_all_contradictions_rejection_warning(mock_db_ctx, caplog):
    """Rejection/Warning test: detect pairs in batch scan."""
    caplog.set_level(logging.WARNING)
    pairs = await scan_all_contradictions(
        db_path=":memory:",
        min_score=0.1,  # Lower score to ensure we catch the Redis <-> Memcached overlap
    )

    # We expect fact 1 and fact 3 to conflict (Redis replaced by Memcached vs Redis for caching)
    found_conflict = False
    for c1, c2 in pairs:
        if (c1.fact_id == 1 and c2.fact_id == 3) or (c1.fact_id == 3 and c2.fact_id == 1):
            found_conflict = True
            break

    assert found_conflict, "Batch scanner failed to find the contradiction pair."

@pytest.mark.asyncio
async def test_scan_all_contradictions_happy_path(monkeypatch, caplog):
    """Happy Path: clean db, no pairs returned."""
    # Mock empty db
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            created_at TEXT
        )
        """
    )
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_connect(db_path):
        yield conn

    monkeypatch.setattr("cortex.guards.contradiction_guard.detector.connect_async_ctx", mock_connect)

    caplog.set_level(logging.WARNING)
    pairs = await scan_all_contradictions(
        db_path=":memory:",
    )

    assert len(pairs) == 0
    await conn.close()

@pytest.mark.asyncio
async def test_scan_all_contradictions_db_error(monkeypatch, caplog):
    """Boundary Condition test: db error in batch scan."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_connect_error(db_path):
        class MockConn:
            row_factory = None
            async def execute(self, *args, **kwargs):
                raise aiosqlite.OperationalError("Simulated DB Error")
        yield MockConn()

    monkeypatch.setattr("cortex.guards.contradiction_guard.detector.connect_async_ctx", mock_connect_error)

    caplog.set_level(logging.WARNING)
    pairs = await scan_all_contradictions(
        db_path=":memory:",
    )

    assert len(pairs) == 0
    assert any("Batch contradiction scan failed" in record.message for record in caplog.records)
