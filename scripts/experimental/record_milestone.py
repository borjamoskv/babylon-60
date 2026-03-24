import asyncio
import json
import os
from decimal import Decimal
from datetime import datetime, timezone

from cortex.cli.common import DEFAULT_DB
from cortex.database.pool import CortexConnectionPool
from cortex.engine_async import AsyncCortexEngine

async def record_milestone():
    db_path = os.environ.get("CORTEX_DB_PATH", DEFAULT_DB)
    print(f"Targeting database: {db_path}")

    pool = CortexConnectionPool(db_path, min_connections=1, max_connections=5, read_only=False)
    await pool.initialize()

    engine = AsyncCortexEngine(pool, db_path)

    # Define milestone data
    project = "CORTEX-CENTAURO"
    action = "MILESTONE_CONSOLIDATION"
    detail = {
        "wave": 8,
        "codename": "Centauro",
        "audit_status": "REMEDIATED",
        "ghost_purge": {
            "status": "COMPLETED",
            "files_removed": "~3000",
            "reason": "URI_HYGIENE_FIX"
        },
        "shannon_compaction": {
            "status": "OPERATIONAL",
            "strategy": "SHANNON_PRUNE",
            "automation": "DAEMON_MONITOR"
        },
        "exergy_recovery": str(Decimal("12.4")),
        "confidence": "C5-Dynamic",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    print(f"Recording milestone {project}/{action}...")

    # We use engine.session() to get a connection for _log_transaction
    async with engine.session() as conn:
        tx_id = await engine._log_transaction(
            conn,
            project=project,
            action=action,
            detail=detail
        )
        print(f"Milestone recorded. Transaction ID: {tx_id}")

        # Force a Merkle Checkpoint
        print("Creating Merkle checkpoint...")
        root = await engine.create_checkpoint()
        if root:
            print(f"Checkpoint created. Root Hash: {root}")
        else:
            print("Checkpoint skipped (batch size not reached or no new tx).")

    await pool.close()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(record_milestone())
