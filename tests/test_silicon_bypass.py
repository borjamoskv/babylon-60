import asyncio
import hashlib
import json
import logging
import subprocess

import aiosqlite
import pytest

from cortex.core.paths import resolve_native_binary
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.working import WorkingMemoryL1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST.SILICON")


async def test_silicon_bypass():
    # 1. Setup Rust Ledger state
    # subject_hash: "rust_rulez" -> content: "Rust is absolute truth"
    subject = "rust_rulez"
    subject_hash = hashlib.sha256(subject.encode()).hexdigest()

    rust_binary = resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN")
    if rust_binary is None:
        pytest.skip("cortex-db binary is not configured for this environment")
    import uuid
    from datetime import datetime

    event_id = f"e-test-{uuid.uuid4().hex[:8]}"
    event = {
        "id": event_id,
        "timestamp": datetime.now().isoformat(),
        "role": "system",
        "content": "Rust is absolute truth",
        "tenant_id": "test_tenant",
        "project_id": "test_project",
        "subject_hash": subject_hash,
        "is_conflict": False,
        "metadata_json": "{}",
    }

    print("\n--- Phase 1: Injecting Fact into Native Silicon ---")
    subprocess.run([str(rust_binary), "record", json.dumps(event)], check=True)

    # 2. Python Orchestrator Setup
    print("--- Phase 2: Python Memory Manager Initiation ---")
    l1 = WorkingMemoryL1()
    encoder = AsyncEncoder()
    l2 = SovereignVectorStoreL2(encoder=encoder, db_path="scratch/test_l2_silicon.db")

    async with aiosqlite.connect("scratch/test_l3_silicon.db") as l3_conn:
        l3 = EventLedgerL3(conn=l3_conn)
        await l3.ensure_table()

        manager = CortexMemoryManager(l1=l1, l2=l2, l3=l3, encoder=encoder)

        # 3. Attempt to store conflicting fact in Python
        print("--- Phase 3: Inducing Python Collision via Silicon Bypass ---")
        # Same subject "rust_rulez", different content
        res = await manager.store(
            tenant_id="test_tenant",
            project_id="test_project",
            content="Python is better than Rust",
            metadata={"subject": subject},
        )

        print(f"Result: {res}")
        assert "conflict" in res
        assert "native:conflict" in res

        print("\n✅ SILICON BYPASS CERTIFIED. Logic validated at binary speed.")
        await l2.close()


if __name__ == "__main__":
    binary = resolve_native_binary("cortex-db", "CORTEX_NATIVE_DB_BIN", "CORTEX_DB_BIN")
    if binary is not None:
        asyncio.run(test_silicon_bypass())
    else:
        print("❌ Rust binary cortex-db not found. Skipping silicon test.")
