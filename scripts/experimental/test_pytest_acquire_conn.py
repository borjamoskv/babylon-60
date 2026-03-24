import pytest
import aiosqlite
from cortex.engine.ledger import SovereignLedger

@pytest.mark.asyncio
async def test_ledger_acquire_conn():
    conn = await aiosqlite.connect(":memory:")
    ledger = SovereignLedger(conn)
    result = ledger._acquire_conn()
    print(f"\n---> TYPE OF _ACQUIRE_CONN: {type(result)}")
    await conn.close()
