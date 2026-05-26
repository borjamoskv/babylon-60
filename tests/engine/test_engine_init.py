"""Unit tests for CortexEngine core — cortex/engine/__init__.py."""

import asyncio
from pathlib import Path
import pytest
import aiosqlite
from cortex.engine import CortexEngine
from cortex.utils.errors import FactNotFound

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_cortex.db"

@pytest.mark.asyncio
async def test_engine_init_basic(db_path):
    """Validate basic engine initialization and path creation."""
    engine = CortexEngine(db_path=db_path)
    assert engine._db_path == db_path
    assert db_path.parent.exists()
    assert engine.system_state == "ACTIVE"
    await engine.close()

@pytest.mark.asyncio
async def test_engine_init_bug01_fix(db_path):
    """Verify BUG-01 fix: detect pool/db_path argument inversion."""
    class MockPool:
        def acquire(self): pass

    mock_pool = MockPool()

    # Correct order: db_path, pool
    engine = CortexEngine(db_path=db_path, pool=mock_pool)
    assert engine._db_path == db_path
    assert engine._pool == mock_pool

    # Inverted order but still valid (should NOT raise TypeError because MockPool has .acquire())
    # The code handles this inversion automatically.
    engine2 = CortexEngine(db_path=mock_pool, pool=db_path)
    assert engine2._pool == mock_pool

    # Truly invalid type should raise TypeError
    with pytest.raises(TypeError) as excinfo:
        CortexEngine(db_path=123, pool=str(db_path))
    assert "Did you swap pool and db_path arguments?" in str(excinfo.value)

@pytest.mark.asyncio
async def test_system_state_management(db_path):
    """Test locking/unlocking engine state."""
    engine = CortexEngine(db_path=db_path)
    assert engine.system_state == "ACTIVE"

    engine.set_system_state("LOCKED")
    assert engine.system_state == "LOCKED"

    engine.set_system_state("RECOVERING")
    assert engine.system_state == "RECOVERING"
    await engine.close()

@pytest.mark.asyncio
async def test_jit_skill_synthesis(db_path):
    """Verify Axiom Ω₄: Skills are synthesized only when needed."""
    engine = CortexEngine(db_path=db_path)
    assert "search" not in engine._skills_verified

    # Trigger search skill synthesis
    engine._synthesize_skill("search")
    assert "search" in engine._skills_verified

    # Trigger store skill synthesis
    engine._synthesize_skill("store")
    assert "store" in engine._skills_verified

    # Multiple calls should be idempotent
    engine._synthesize_skill("search")
    assert len(engine._skills_verified) == 2
    await engine.close()

@pytest.mark.asyncio
async def test_session_lifecycle(db_path):
    """Test the session() async context manager and connection acquisition."""
    engine = CortexEngine(db_path=db_path)

    async with engine.session() as conn:
        assert isinstance(conn, aiosqlite.Connection)
        # Verify we can execute queries
        async with conn.execute("SELECT 1") as cursor:
            row = await cursor.fetchone()
            assert row[0] == 1

    # Connection should still be open internally if cached
    assert engine._conn is not None
    await engine.close()
    assert engine._conn is None

@pytest.mark.asyncio
async def test_engine_close_cleanup(db_path):
    """Ensure engine cleanup closes connections and tasks."""
    engine = CortexEngine(db_path=db_path)
    await engine.init_db()

    # Add a dummy post-commit task
    async def dummy_task():
        await asyncio.sleep(0.1)

    task = asyncio.create_task(dummy_task())
    engine._post_commit_tasks.add(task)

    await engine.close()
    assert engine._conn is None
    assert not engine._post_commit_tasks
    assert engine._system_state == "ACTIVE" # Should still be ACTIVE but closed

@pytest.mark.asyncio
async def test_retrieve_not_found(db_path):
    """Test retrieve method error handling."""
    engine = CortexEngine(db_path=db_path)
    await engine.init_db()

    with pytest.raises(FactNotFound):
        await engine.retrieve(999999)

    await engine.close()
