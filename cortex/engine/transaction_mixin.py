"""Transaction mixin — log, verify, and process ledger events."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Any

import aiosqlite

from cortex.engine.mixins.base import EngineMixinBase
from cortex.memory.temporal import now_iso

__all__ = ["TransactionMixin"]

logger = logging.getLogger("cortex.transactions")


class TransactionMixin(EngineMixinBase):
    """Sovereign Ledger — Immutable Transaction Log with Cryptographic Hash Chain.

    Every write operation produces a transaction record chained to its predecessor
    via ``compute_tx_hash(prev_hash, project, action, detail, timestamp)``.
    The chain is verified by ``ImmutableLedger.audit_integrity_async()``.

    CDC Pattern: ``_log_transaction()`` is the single write-path for all
    state mutations (store, deprecate, quarantine, unquarantine).
    """

    async def _get_or_create_ledger(self):
        """Resolve the backing ledger from the live pool/connection."""
        if getattr(self, "_ledger", None) is not None:
            return self._ledger

        from cortex.ledger import ImmutableLedger

        backend = getattr(self, "_pool", None) or getattr(self, "_conn", None)
        if backend is None:
            async with self.session() as conn:  # type: ignore[reportAttributeAccessIssue]
                backend = conn

        self._ledger = ImmutableLedger(backend)
        return self._ledger

    def _schedule_checkpoint(self) -> None:
        """Checkpoint out of band so writes don't block on Merkle batching."""
        if getattr(self, "_ledger_checkpoint_task", None) is not None:
            if not self._ledger_checkpoint_task.done():
                return

        self._ledger_checkpoint_task = asyncio.create_task(self._run_checkpoint())

    async def _run_checkpoint(self) -> None:
        """Best-effort checkpoint worker."""
        try:
            if getattr(self, "_ledger", None):
                await self._ledger.create_checkpoint_async()
        except (sqlite3.Error, OSError, RuntimeError, AttributeError) as e:
            logger.warning("Auto-checkpoint failed: %s", e)
            from cortex.telemetry.metrics import metrics

            metrics.inc(
                "cortex_ledger_checkpoint_failures_total",
                meta={"error": str(e)},
            )
        finally:
            self._ledger_checkpoint_task = None

    async def _log_transaction(
        self,
        conn: aiosqlite.Connection,
        project: str,
        action: str,
        detail: dict[str, Any],
        tenant_id: str = "default",
    ) -> int:
        from cortex.utils.canonical import canonical_json, compute_tx_hash

        dj = canonical_json(detail)
        ts = now_iso()
        cursor = await conn.execute(
            "SELECT hash FROM transactions WHERE tenant_id = ? ORDER BY id DESC LIMIT 1",
            (tenant_id,),
        )
        prev = await cursor.fetchone()
        await cursor.close()
        ph = prev[0] if prev else "GENESIS"
        th = compute_tx_hash(ph, project, action, dj, ts)

        c = await conn.execute(
            "INSERT INTO transactions "
            "(tenant_id, project, action, detail, prev_hash, hash, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tenant_id, project, action, dj, ph, th, ts),
        )
        tx_id = c.lastrowid

        if getattr(self, "_ledger", None):
            self._ledger.record_write()
            batch_size = max(int(self._ledger.adaptive_batch_size), 1)
            if tx_id is not None and int(tx_id) % batch_size == 0:
                self._schedule_checkpoint()

        return int(tx_id) if tx_id is not None else 0

    async def verify_ledger(self) -> dict[str, Any]:
        """Verify the integrity of the sovereign ledger (Operation Void)."""
        ledger = await self._get_or_create_ledger()
        return await ledger.audit_integrity_async()
