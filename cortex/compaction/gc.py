"""CORTEX v5.0 — Vector Memory Garbage Collection Pipeline.

Tombstoned facts are immutable domain records. This collector now reports
physical-deletion candidates but fails closed instead of deleting facts, vectors,
or consensus records outside a tenant-scoped canonical purge ledger.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("cortex.gc")


class GarbageCollector:
    """Garbage collector gate for tombstoned facts."""

    def __init__(self, engine: AsyncCortexEngine):
        self.engine = engine

    def _is_off_peak(self) -> bool:
        """Determines if current time is within off-peak hours (02:00 - 05:00)."""
        now = datetime.now(timezone.utc)
        return 2 <= now.hour < 5

    async def run_gc(self, batch_size: int = 500, force: bool = False) -> dict[str, Any]:
        """
        Detect tombstoned facts and block physical deletion.

        Physical fact deletion requires a tenant-scoped canonical purge ledger;
        this background job cannot provide that boundary, so it reports candidates
        without mutating persisted facts or related indexes.
        """
        if not self._is_off_peak() and not force:
            logger.info("Garbage Collector: Skipping execution (peak hours detected).")
            return {
                "status": "skipped",
                "reason": "peak_hours",
                "deleted_facts": 0,
                "deleted_embeddings": 0,
                "errors": [],
            }

        stats: dict[str, Any] = {
            "status": "completed",
            "deleted_facts": 0,
            "deleted_embeddings": 0,
            "blocked_facts": 0,
            "errors": [],
        }

        async with self.engine.session() as conn:
            cursor = await conn.execute(
                "SELECT id FROM facts WHERE is_tombstoned = 1 LIMIT ?", (batch_size,)
            )
            rows = await cursor.fetchall()

            if not rows:
                logger.info("Garbage Collector: No tombstoned facts found.")
                return stats

            fact_ids = [row[0] for row in rows]
            stats["status"] = "blocked"
            stats["reason"] = "canonical_purge_required"
            stats["blocked_facts"] = len(fact_ids)
            logger.error(
                "Garbage Collector: blocked physical deletion of %d tombstoned facts; "
                "canonical tenant-scoped purge ledger required.",
                len(fact_ids),
            )

        logger.info(
            "Garbage Collector Run Complete: %d facts and %d vectors physically removed.",
            stats["deleted_facts"],
            stats["deleted_embeddings"],
        )
        return stats

    async def _execute_physical_deletion(self, conn: Any, fact_ids: list[Any]) -> None:
        """Fail closed for legacy callers that still reach the destructive hook."""
        _ = (conn, fact_ids)
        raise RuntimeError(
            "Physical fact deletion is blocked; use a canonical tenant-scoped purge ledger."
        )
