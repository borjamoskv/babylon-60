import asyncio
import json
import logging
import os

import aiosqlite

from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.working import WorkingMemoryL1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST.EPISTEMOLOGY")


async def test_conflict_detection():
    db_path = "scratch/test_cortex.db"
    ledger_path = "scratch/test_ledger.db"
    for p in [db_path, ledger_path]:
        if os.path.exists(p):
            os.remove(p)

    encoder = AsyncEncoder()
    l1 = WorkingMemoryL1()

    async with aiosqlite.connect(ledger_path) as conn:
        l3 = EventLedgerL3(conn=conn)
        await l3.ensure_table()

        l2 = SovereignVectorStoreL2(encoder=encoder, db_path=db_path)
        manager = CortexMemoryManager(l1=l1, l2=l2, l3=l3, encoder=encoder)

        tenant = "test_tenant"
        project = "test_project"
        subject = "capital_francia"

        # 1. Store Fact A
        print("\n--- STEP 1: Storing Fact A ---")
        res1 = await manager.store(
            tenant_id=tenant,
            project_id=project,
            content="La capital de Francia es París.",
            metadata={"source": "v1", "subject": subject},
        )
        print(f"RESULT 1: {res1}")

        # 2. Store Contradictory Fact (Conflict check)
        print("\n--- STEP 2: Storing Contradictory Fact ---")
        res2 = await manager.store(
            tenant_id=tenant,
            project_id=project,
            content="La capital de Francia es Lyon.",
            metadata={"source": "v2", "subject": subject},
        )
        print(f"RESULT 2: {res2}")

        # 3. Verify Conflict in result
        assert "conflict" in res2, f"Expected conflict for Res2, got {res2}"

        # 4. Verify Immutable Record in Ledger (L3)
        print("\n--- STEP 3: Verifying Ledger (L3) ---")
        async with conn.execute(
            "SELECT event_id, role, content, metadata FROM memory_events WHERE content LIKE 'EPISTEMIC_CONFLICT%' LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None, "Conflict event NOT found in Ledger L3 (memory_events table)!"
            print(f"✅ LEDGER VERIFIED: {row[0]} | {row[1]} | {row[2]}")

            meta = json.loads(row[3])
            assert meta["type"] == "epistemic_conflict", "Metadata type mismatch"
            assert "subject_hash" in meta, "Subject hash missing from ledger metadata"

        print("\n✅ C5-REAL Integrity CERTIFIED.")
        await l2.close()


if __name__ == "__main__":
    asyncio.run(test_conflict_detection())
