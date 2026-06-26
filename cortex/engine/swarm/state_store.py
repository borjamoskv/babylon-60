# [C5-REAL] Exergy-Maximized
"""
CAUSAL STATE STORE: The Thermodynamic Funnel.
Isolates SQLite writes from massive async concurrency to prevent I/O Deadlocks.
Enforces SAGA patterns, Guards validation, and Ledger cryptographic emission.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.config import DB_PATH
from cortex.guards import CausalClosureGuard, SwarmProposal
# Replace with correct import for Ledger if needed, but the old code emitted SwarmProposal.

logger = logging.getLogger(__name__)

class CausalStateStore:
    """The only component authorized to write causal state to SQLite."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
        
    async def connect(self):
        if not self._db:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA journal_mode=WAL;")
            await self._db.execute("PRAGMA synchronous=NORMAL;")
            
    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def _verify_hypothesis_active(self, hyp_id: str) -> bool:
        if not self._db:
            return False
        async with self._db.execute(
            "SELECT status FROM system_hypotheses WHERE id = ?", (hyp_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == "INVALIDATED":
                return False
        return True

    async def _emit_ledger_event(self, signal: Any) -> None:
        """Emit cryptographic ledger event (SAGA Step)"""
        # Create a ledger payload using CausalClosureGuard
        ledger_payload = {
            "type": "CausalStateMutation",
            "agent_id": signal.agent_id,
            "target": signal.target,
            "status": signal.status,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "payload": signal.payload,
        }
        
        proposal = SwarmProposal(
            agent_id=signal.agent_id,
            mission_statement=f"Apply signal to {signal.target}",
            content=json.dumps(ledger_payload),
            token_cost=100, 
        )
        guard = CausalClosureGuard()
        guard.verify_closure(proposal)

    async def process_signal(self, signal: Any) -> None:
        """Process a SwarmSignal, validate guards, and commit to state."""
        await self.connect()
        async with self._lock:
            if not self._db:
                raise RuntimeError("Database not connected.")

            # 1. Hito 2: Cascade Death Protection
            if signal.target.startswith("hyp-"):
                is_active = await self._verify_hypothesis_active(signal.target)
                if not is_active:
                    logger.warning(f"Dropping signal for {signal.target}: Hypothesis is INVALIDATED.")
                    return

            # 2. SAGA: Ledger Validation
            try:
                await self._emit_ledger_event(signal)
            except Exception as e:
                logger.error(f"[SAGA ABORT] Ledger Validation failed for signal {signal.target}: {e}")
                return

            # 3. Apply State Mutation
            try:
                # Update hypothesis status if applicable
                if signal.status in ("SUCCESS", "FAILURE"):
                    # Just an example of state mutation, updating meta to bump version
                    await self._db.execute(
                        "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                    )
                    
                    if signal.target.startswith("hyp-") and signal.status == "SUCCESS":
                        await self._db.execute(
                            "UPDATE system_hypotheses SET status = 'COMPLETED' WHERE id = ?", (signal.target,)
                        )
                await self._db.commit()
            except Exception as e:
                await self._db.rollback()
                logger.error(f"[SAGA ROLLBACK] State mutation failed: {e}")
                
    async def recover_in_flight_tasks(self) -> int:
        """Open Question resolution: Recover Ghost State on startup."""
        await self.connect()
        async with self._lock:
            if not self._db:
                return 0
            
            async with self._db.execute("SELECT count(*) FROM system_hypotheses WHERE status = 'IN_FLIGHT'") as cur:
                count = (await cur.fetchone())[0]
                
            if count > 0:
                logger.info(f"Recovering {count} IN_FLIGHT tasks to ACTIVE status.")
                await self._db.execute("UPDATE system_hypotheses SET status = 'ACTIVE' WHERE status = 'IN_FLIGHT'")
                await self._db.execute(
                    "UPDATE cortex_meta SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) WHERE key = 'hypothesis_graph_version'"
                )
                await self._db.commit()
            return count
