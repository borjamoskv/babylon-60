"""Tests for cortex.daemon.annihilator — structural entropy and memory exergy daemon."""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest
import aiosqlite

from cortex.daemon.annihilator import AnnihilatorDaemon


@pytest.fixture
async def temp_db(tmp_path: Path) -> str:
    import sqlite3
    from cortex.ledger import SovereignLedger

    db_file = tmp_path / "test_annihilator.db"
    db_path = str(db_file)

    conn = sqlite3.connect(db_path)
    ledger = SovereignLedger(conn)
    # Insert a real transaction using ledger to ensure valid hash continuity
    ledger.record_transaction(
        project="cortex-guard",
        action="GUARD_VERDICT",
        detail={
            "verdict": "ANNIHILATE",
            "reason": "Test Purge",
            "target": "SYSTEM_DB",
            "action_type": "SYSTEM_PURGE",
        },
    )
    conn.close()

    return db_path


class TestAnnihilatorDaemon:
    """Tests for the AnnihilatorDaemon background worker and purging."""

    def test_daemon_init(self):
        """Verify proper initialization of configuration thresholds."""
        daemon = AnnihilatorDaemon(
            db_path="/tmp/nonexistent.db", entropy_threshold=4.5, memory_threshold_mb=256.0
        )
        assert daemon.db_path == "/tmp/nonexistent.db"
        assert daemon.entropy_threshold == 4.5
        assert daemon.memory_threshold_mb == 256.0
        assert daemon._is_running is False

    def test_get_rss_memory_mb(self):
        """Measure current RSS memory, asserting positive non-zero value."""
        daemon = AnnihilatorDaemon(db_path="/tmp/nonexistent.db")
        mem = daemon._get_rss_memory_mb()
        assert isinstance(mem, float)
        assert mem > 0.0

    async def test_measure_entropy(self, temp_db: str):
        """Verify database entropy is computed successfully based on heuristics."""
        daemon = AnnihilatorDaemon(db_path=temp_db)
        entropy = await daemon.measure_entropy()
        assert isinstance(entropy, float)
        assert entropy >= 0.0

    async def test_purge(self, temp_db: str):
        """Verify execution of a database structural purge and vacuum."""
        daemon = AnnihilatorDaemon(db_path=temp_db)
        results = await daemon.purge()
        assert results.get("vacuumed") is True
        assert "error" not in results

        # Verify entry in ledger/transactions
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute(
                "SELECT count(*) FROM transactions WHERE detail LIKE '%ANNIHILATE%'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] >= 1

    async def test_run_loop_trigger_memory_gc(self, temp_db: str, monkeypatch):
        """Verify the background loop triggers GC and logs a memory event when threshold is exceeded."""
        daemon = AnnihilatorDaemon(
            db_path=temp_db, memory_threshold_mb=0.01
        )  # tiny threshold to trigger memory check

        gc_collected = False

        def mock_gc_collect():
            nonlocal gc_collected
            gc_collected = True
            return 0

        monkeypatch.setattr("gc.collect", mock_gc_collect)

        # We run the loop once by subclassing or cancelling immediately
        async def run_once():
            task = asyncio.create_task(daemon.run_loop(interval_seconds=10))
            await asyncio.sleep(0.1)
            daemon.stop()
            try:
                await task
            except asyncio.CancelledError:
                pass

        await run_once()

        assert gc_collected is True

        # Check that the JIT_MEMORY_PURGE is recorded in the transaction ledger
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute(
                "SELECT count(*) FROM transactions WHERE detail LIKE '%JIT_MEMORY_PURGE%'"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] >= 1
