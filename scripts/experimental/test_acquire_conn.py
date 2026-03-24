import asyncio
import aiosqlite
from cortex.engine.ledger import SovereignLedger

async def main():
    conn = await aiosqlite.connect(":memory:")
    ledger = SovereignLedger(conn)
    result = ledger._acquire_conn()
    print(f"Type of _acquire_conn(): {type(result)}")
    try:
        async with result as c:
            print("Successfully entered context manager")
    except Exception as e:
        print(f"Error entering context manager: {type(e).__name__}: {e}")
    await conn.close()

asyncio.run(main())
