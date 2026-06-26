import pytest
import sqlite3
import asyncio
from unittest.mock import patch, AsyncMock
import logging
from cortex.database.core import causal_write

logger = logging.getLogger(__name__)

class InducedCrashError(Exception):
    """Exception raised specifically for simulating a system crash."""
    pass

@pytest.mark.asyncio
async def test_crash_before_causal_write(engine):
    """
    Test scenario where the system crashes before causal write authorization.
    Expected: No DB mutation and no Ledger mutation.
    """
    from cortex.database.core import causal_write as original_causal_write
    
    with patch("cortex.engine.core.store_mixin.causal_write", side_effect=InducedCrashError("Crash before causal_write")):
        try:
            await engine.memory.store(
                project="TEST", 
                action="CRASH_TEST", 
                content={"key": "val"}
            )
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact should not be written to DB"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should not be written to Ledger"


@pytest.mark.asyncio
async def test_crash_after_db_write_before_ledger(engine):
    """
    Test scenario where DB is updated but crash occurs before ledger logic completes.
    Since they share the same SQLite connection (and transaction), the crash should rollback the DB write.
    """
    original_log = engine._log_transaction
    
    async def crashing_log_transaction(*args, **kwargs):
        raise InducedCrashError("Crash inside ledger logic")
    
    with patch.object(engine, "_log_transaction", new=crashing_log_transaction):
        try:
            await engine.memory.store(
                project="TEST", 
                action="CRASH_TEST_2", 
                content={"key": "val2"}
            )
        except InducedCrashError:
            pass
            
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST_2'")
        fact_count = (await cursor.fetchone())[0]
        # Because we are using an async transaction context, if an exception propagates, 
        # aiosqlite should issue a ROLLBACK automatically.
        assert fact_count == 0, "Fact write should be rolled back due to uncommitted transaction"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST_2'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should not exist"


@pytest.mark.asyncio
async def test_crash_during_commit(engine):
    """
    Test scenario where everything finishes, but commit fails.
    Expected: Rollback of both DB and Ledger writes.
    """
    original_commit = None
    
    # We'll intercept connect_async_ctx so we can mock commit on the yielded connection
    from cortex.database.core import connect_async_ctx as original_connect_async_ctx
    
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mocked_connect_async_ctx(*args, **kwargs):
        async with original_connect_async_ctx(*args, **kwargs) as conn:
            # mock the commit method
            original_commit = conn.commit
            async def crashing_commit(*args, **kwargs):
                raise InducedCrashError("Crash during commit")
            conn.commit = crashing_commit
            try:
                yield conn
            finally:
                conn.commit = original_commit

    with patch("cortex.engine.core.store_mixin.connect_async_ctx", new=mocked_connect_async_ctx):
        try:
            await engine.memory.store(
                project="TEST", 
                action="CRASH_TEST_3", 
                content={"key": "val3"}
            )
        except InducedCrashError:
            pass

    async with engine.session() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM facts WHERE project = 'TEST' AND action = 'CRASH_TEST_3'")
        fact_count = (await cursor.fetchone())[0]
        assert fact_count == 0, "Fact write should be rolled back"
        
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE project = 'TEST' AND action = 'CRASH_TEST_3'")
        tx_count = (await cursor.fetchone())[0]
        assert tx_count == 0, "Transaction should be rolled back"
