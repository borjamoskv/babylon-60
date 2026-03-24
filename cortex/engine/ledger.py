"""
CORTEX v8 — Sovereign Immutable Ledger (CHRONOS-1 Standard).

Axiom Reference:
- Ω₃ (Byzantine Default): "I verify, then trust. Never reversed."
- Ω₂ (Entropic Asymmetry): "Merkle Trees reduce trust-cost from O(N) to O(log N)."

This module consolidates the legacy dual-ledger architecture into a single,
async-first trust substrate.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.database.pool import CortexConnectionPool

from cortex import config
from cortex.consensus.merkle import MerkleTree
from cortex.utils.canonical import compute_tx_hash

__all__ = ["SovereignLedger"]

logger = logging.getLogger("cortex.ledger")


@dataclass(frozen=True)
class MerkleNode:
    """A node within the Merkle Tree (V8 Immutable)."""

    hash: str
    left: MerkleNode | None = None
    right: MerkleNode | None = None
    is_leaf: bool = False


class SovereignLedger:
    """The Custodian of Immutable History (CORTEX Wave 8 Unified)."""

    WRITE_RATE_WINDOW = 60  # seconds
    HIGH_WRITE_THRESHOLD = 10  # writes/sec triggers adaptive reduction

    def __init__(self, pool: CortexConnectionPool):
        self.pool = pool
        self._write_timestamps: deque[float] = deque(maxlen=5000)

    import contextlib

    @contextlib.asynccontextmanager
    async def _acquire_conn(self):
        if hasattr(self.pool, "acquire"):
            async with self.pool.acquire() as conn:
                yield conn
        elif hasattr(self.pool, "get_conn"):
            conn = await self.pool.get_conn()
            yield conn
        else:
            yield self.pool

    def record_write_metric(self) -> None:
        """Call on every transaction to track write rate for adaptive checkpointing."""
        self._write_timestamps.append(time.monotonic())

    @property
    def adaptive_batch_size(self) -> int:
        """Compute batch size based on recent write rate."""
        now = time.monotonic()
        cutoff = now - self.WRITE_RATE_WINDOW
        recent = sum(1 for t in self._write_timestamps if t > cutoff)
        rate = recent / self.WRITE_RATE_WINDOW
        if rate > self.HIGH_WRITE_THRESHOLD:
            return config.CHECKPOINT_MIN
        return config.CHECKPOINT_MAX

    async def record_transaction(
        self, project: str, action: str, detail: Any = None, tenant_id: str = "default"
    ) -> str:
        """Commit a high-value probabilistic decision into deterministic history."""
        detail_json = json.dumps(detail, sort_keys=True) if detail else "{}"
        ts = datetime.now(timezone.utc).isoformat()
        self.record_write_metric()

        async with self._acquire_conn() as conn:
            # Enforce an EXCLUSIVE lock to prevent race conditions during hash-chain read-compute-write cycle.
            await conn.execute("BEGIN EXCLUSIVE")
            try:
                cursor = await conn.execute(
                    "SELECT hash FROM transactions ORDER BY id DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                prev_hash = row[0] if row else "GENESIS"

                # CHRONOS-1 (v8) Canonical Hash
                new_hash = compute_tx_hash(prev_hash, project, action, detail_json, ts)

                await conn.execute(
                    "INSERT INTO transactions "
                    "(project, action, detail, prev_hash, hash, timestamp, tenant_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (project, action, detail_json, prev_hash, new_hash, ts, tenant_id),
                )
                await conn.commit()
                return new_hash
            except Exception as e:
                await conn.rollback()
                logger.error("Ledger Write Failure: %s", e)
                raise

    async def create_checkpoint(self) -> str | None:
        """Create a Merkle tree checkpoint for recent transactions (Adaptive)."""
        batch_size = self.adaptive_batch_size

        async with self._acquire_conn() as conn:
            cursor = await conn.execute("SELECT MAX(tx_end_id) FROM merkle_roots")
            row = await cursor.fetchone()
            last_covered = row[0] or 0 if row else 0

            cursor = await conn.execute(
                "SELECT id, hash FROM transactions WHERE id > ? ORDER BY id", (last_covered,)
            )
            rows = await cursor.fetchall()
            if not rows or (len(rows) < batch_size and last_covered > 0):
                return None

            hashes = [r[1] for r in rows]
            tree = MerkleTree(hashes)
            root = tree.root
            start_id, end_id = rows[0][0], rows[-1][0]

            await conn.execute(
                "INSERT INTO merkle_roots (root_hash, tx_start_id, tx_end_id, tx_count) VALUES (?, ?, ?, ?)",
                (root, start_id, end_id, len(rows)),
            )
            await conn.commit()
            logger.info("Created Merkle checkpoint (TX %d-%d)", start_id, end_id)
            return root

    async def audit_integrity(self) -> dict:
        """Verify hash chain continuity and Merkle checkpoints across the entire history."""
        violations = []
        tx_count = 0

        async with self._acquire_conn() as conn:
            cursor = await conn.execute(
                "SELECT id, project, action, detail, prev_hash, hash, timestamp FROM transactions ORDER BY id"
            )

            expected_prev = "GENESIS"
            while True:
                row = await cursor.fetchone()
                if not row:
                    break
                tid, proj, act, det, prev, h, ts = row
                tx_count += 1

                if prev != expected_prev:
                    violations.append(
                        {
                            "id": tid,
                            "type": "CHAIN_BREAK",
                            "expected": expected_prev,
                            "actual": prev,
                        }
                    )

                computed = compute_tx_hash(prev, proj, act, det, ts)
                if computed != h:
                    violations.append(
                        {"id": tid, "type": "TAMPER_DETECTED", "stored": h, "computed": computed}
                    )
                expected_prev = h

            # Verify Merkle Checkpoints
            cursor = await conn.execute(
                "SELECT root_hash, tx_start_id, tx_end_id FROM merkle_roots"
            )
            roots = await cursor.fetchall()
            for stored_root, start, end in roots:
                c = await conn.execute(
                    "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
                    (start, end),
                )
                rows = await c.fetchall()
                hashes = [r[0] for r in rows]
                computed_r = MerkleTree(hashes).root
                if computed_r != stored_root:
                    violations.append(
                        {
                            "range": f"{start}-{end}",
                            "type": "MERKLE_MISMATCH",
                            "stored": stored_root,
                            "computed": computed_r,
                        }
                    )

            return {"valid": not violations, "violations": violations, "tx_count": tx_count}
