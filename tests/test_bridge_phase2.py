import asyncio
import logging
import os
import sqlite3

import aiosqlite

from cortex.ledger.store import LedgerStore
from cortex.ledger.writer import LedgerWriter
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.working import WorkingMemoryL1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST.BRIDGE")


async def test_selective_bridge():
    db_path = "scratch/test_cortex.db"
    l3_path = "scratch/test_l3.db"
    global_path = "scratch/test_global.db"

    # Clean up
    for p in [db_path, l3_path, global_path]:
        if os.path.exists(p):
            os.remove(p)

    encoder = AsyncEncoder()
    l1 = WorkingMemoryL1()

    # Global Ledger Setup
    global_store = LedgerStore(global_path)

    # Mock queue for testing
    class MockQueue:
        def enqueue(self, event_id):
            pass

    global_writer = LedgerWriter(global_store, MockQueue())

    async with aiosqlite.connect(l3_path) as conn:
        l3 = EventLedgerL3(conn=conn)
        await l3.ensure_table()

        l2 = SovereignVectorStoreL2(encoder=encoder, db_path=db_path)
        manager = CortexMemoryManager(
            l1=l1, l2=l2, l3=l3, encoder=encoder, global_writer=global_writer
        )

        tenant = "test_tenant"
        project = "test_project"
        subject = "collision_subject"

        # 1. Store Baseline
        await manager.store(
            tenant_id=tenant,
            project_id=project,
            content="Fact Original",
            metadata={"subject": subject},
        )

        # 2. Case: HIGH SEVERITY CONFLICT (Should Bridge)
        print("\n--- CASE A: High Severity Conflict (Expect Bridge) ---")
        res_high = await manager.store(
            tenant_id=tenant,
            project_id=project,
            content="Fact Contradictorio A",
            metadata={"subject": subject, "severity": "HIGH"},
        )
        assert "conflict" in res_high

        await asyncio.sleep(0.5)

        # Verify L3
        async with conn.execute("SELECT count(*) FROM memory_events") as c:
            l3_count = (await c.fetchone())[0]
            print(f"L3 Events: {l3_count}")
            assert l3_count >= 2

        # Verify Global
        with sqlite3.connect(global_path) as g_conn:
            g_conn.row_factory = sqlite3.Row
            row = g_conn.execute(
                "SELECT count(*) FROM ledger_events WHERE action = 'CONFLICT_DETECTION'"
            ).fetchone()
            print(f"Global Conflict Events: {row[0]}")
            assert row[0] == 1

        # 3. Case: LOW SEVERITY CONFLICT (Should NOT Bridge)
        print("\n--- CASE B: Low Severity Conflict (Expect NO Bridge) ---")
        res_low = await manager.store(
            tenant_id=tenant,
            project_id=project,
            content="Fact Contradictorio B",
            metadata={"subject": subject, "severity": "LOW"},
        )
        assert "conflict" in res_low

        # Verify Global count remains 1
        with sqlite3.connect(global_path) as g_conn:
            row = g_conn.execute(
                "SELECT count(*) FROM ledger_events WHERE action = 'CONFLICT_DETECTION'"
            ).fetchone()
            print(f"Global Conflict Events (after low): {row[0]}")
            assert row[0] == 1

        print("\n✅ PHASE II: Selective Bridge CERTIFIED.")
        await l2.close()


if __name__ == "__main__":
    asyncio.run(test_selective_bridge())
