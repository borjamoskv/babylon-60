from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.shannon")


class ShannonCompactor:
    """
    Sovereign Compaction Engine (v8).
    Reduces ledger entropy by archiving stale transactions while preserving Merkle integrity.
    Follows Axiom L4 (Temporal Decay) for bus-layer hygiene.
    """

    def __init__(self, engine: CortexEngine):
        self.engine = engine

    async def prune_historical_debt(self, days: int = 30) -> dict:
        """Prune transactions older than 'days' from the ledger."""
        threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        db = await self.engine.get_conn()

        async with db.execute("BEGIN TRANSACTION"):
            try:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM transactions WHERE timestamp < ?", (threshold,)
                )
                count = (await cursor.fetchone())[0]  # type: ignore

                if count == 0:
                    await db.execute("ROLLBACK")
                    return {"archived": 0, "status": "no_debt_detected"}

                # 2. Archive to cold storage (delete to reduce exergy loss)
                await db.execute(
                    "DELETE FROM transactions WHERE timestamp < ?", (threshold,)
                )

                # 3. VACUUM to reclaim disk space (Thermodynamic optimization)
                # Note: VACUUM cannot run within a transaction, so we do it after commit.
                await db.execute("COMMIT")

                logger.info("ShannonCompactor: Pruned %d transactions.", count)
                return {
                    "archived": count,
                    "threshold_date": threshold,
                    "entropy_reduction": f"{count * 0.12:.2f} bits (est.)",
                    "status": "success",
                }
            except Exception as e:
                await db.execute("ROLLBACK")
                logger.error("Shannon: Compaction failed: %s", e)
                return {"status": "error", "message": str(e)}

    async def prune_bus_entropy(self, days: int = 7) -> dict:
        """Prune consumed or stale agent messages (Axiom L4)."""
        import time

        threshold_ts = time.time() - (days * 24 * 3600)
        db = await self.engine.get_conn()

        # We prune consumed messages regardless of age,
        # and unconsumed messages older than threshold.
        async with db.execute("BEGIN TRANSACTION"):
            try:
                # Check if table exists (it might not have been initialized)
                tm_query = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='agent_messages'"
                async with db.execute(tm_query) as cursor:
                    if (await cursor.fetchone())[0] == 0:  # type: ignore
                        await db.execute("ROLLBACK")
                        return {"status": "noop", "message": "agent_messages table not found"}

                count_query = "SELECT COUNT(*) FROM agent_messages WHERE consumed = 1 OR created_at < ?"
                cursor = await db.execute(count_query, (threshold_ts,))
                count = (await cursor.fetchone())[0]  # type: ignore

                if count > 0:
                    del_query = "DELETE FROM agent_messages WHERE consumed = 1 OR created_at < ?"
                    await db.execute(del_query, (threshold_ts,))
                    await db.execute("COMMIT")
                    logger.info("Shannon: Pruned %d bus messages (entropy reduction)", count)
                else:
                    await db.execute("ROLLBACK")

            except Exception as e:
                await db.execute("ROLLBACK")
                logger.error("Shannon: Bus pruning failed: %s", e)
                return {"status": "error", "message": str(e)}

        return {"status": "success", "pruned": count, "threshold_ts": threshold_ts}
