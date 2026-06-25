"""
Tests for Ouroboros L6: Thermodynamic Defragmentation (Phase 2).
"""

import pytest
import sqlite3
import aiosqlite
import os

from cortex.engine.autopoiesis.thermodynamic_defrag import ThermodynamicDefragmenter

DB_PATH = "tests/test_defrag.db"

@pytest.fixture
async def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            CREATE TABLE facts (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                confidence TEXT,
                created_at DATETIME
            )
            """
        )
        
        # Insert 10 C5-REAL (Useful) vectors
        for i in range(10):
            await conn.execute(
                "INSERT INTO facts (id, tenant_id, confidence, created_at) VALUES (?, ?, ?, datetime('now'))",
                (f"useful_{i}", "default", "C5-REAL")
            )
            
        # Insert 100 C0 (Entropic/Useless) vectors, aged artificially
        for i in range(100):
            await conn.execute(
                "INSERT INTO facts (id, tenant_id, confidence, created_at) VALUES (?, ?, ?, datetime('now', '-30 days'))",
                (f"entropic_{i}", "default", "C0")
            )
            
        await conn.commit()
        
    yield DB_PATH
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.mark.asyncio
async def test_thermodynamic_defragmentation(setup_db):
    db_path = setup_db
    
    async with aiosqlite.connect(db_path) as conn:
        # Initial count
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE tenant_id = 'default'")
        initial_count = (await cursor.fetchone())[0]
        assert initial_count == 110
        
        # Run defrag
        purged = await ThermodynamicDefragmenter.defragment_tenant(conn, "default")
        
        # Check assertions
        assert purged == 100, f"Expected 100 purged, got {purged}"
        
        # Verify useful facts remain
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE tenant_id = 'default'")
        final_count = (await cursor.fetchone())[0]
        assert final_count == 10
        
        # Verify that all remaining facts are useful
        cursor = await conn.execute("SELECT id FROM facts WHERE tenant_id = 'default'")
        rows = await cursor.fetchall()
        for row in rows:
            assert "useful" in row[0]
