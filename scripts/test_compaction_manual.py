import asyncio
import os
import tempfile
import logging
from pathlib import Path

import aiosqlite
from cortex.audit.ledger import EnterpriseAuditLedger

logging.basicConfig(level=logging.DEBUG)

async def main():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "audit.db"
    
    os.environ["CORTEX_LEDGER_MAX_BATCH"] = "2"
    os.environ["CORTEX_TEST_ENV"] = "1"
    
    print("Connecting to DB...")
    conn = await aiosqlite.connect(str(db_path))
    ledger = EnterpriseAuditLedger(conn)
    await ledger.ensure_table()
    
    print("Inserting rows...")
    for i in range(10):
        await ledger.log_action(
            tenant_id="tenant_1",
            actor_role="admin",
            actor_id="user_test",
            action="CREATE",
            resource=f"file_{i}.txt"
        )
        await asyncio.sleep(0.01)
    
    print("Verifying chain...")
    verify_res = await ledger.verify_chain()
    print("Verify 1:", verify_res)
    
    snapshot_dir = Path(temp_dir) / "snapshots"
    print("Running compaction...")
    compaction_res = await ledger.compact_ledger(max_rows=5, snapshot_dir=snapshot_dir)
    print("Compaction res:", compaction_res)
    
    print("Verifying chain again...")
    verify_res2 = await ledger.verify_chain()
    print("Verify 2:", verify_res2)
    
    print("Closing ledger...")
    await ledger.close()
    await conn.close()
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
