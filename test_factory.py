# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------

import asyncio
import sqlite3


import aiosqlite





class SovereignConnection(sqlite3.Connection):
    def set_authorizer(self, cb):
        raise Exception('blocked')

async def main():
    async with aiosqlite.connect(':memory:', factory=SovereignConnection) as db:
        await db._execute(lambda c: c.set_authorizer(None), db._conn)

asyncio.run(main())
