# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX v5.3 — L3 Event Ledger (Immutable Event Sourcing).

Every interaction, thought, and state change is recorded as an immutable
event in SQLite WAL via `cortex.db`. If L1 or L2 collapse, the full
cognitive state can be reconstructed by replaying L3 events.

Uses the hardened `cortex.db.connect_async()` factory for zero-lock I/O.
"""

from __future__ import annotations

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.memory.models import MemoryEvent

try:
    from cortex.extensions.security.tenant import get_tenant_id
except Exception:

    def get_tenant_id() -> str:
        return "default"


__all__ = ["EventLedgerL3"]

logger = logging.getLogger("cortex.memory.ledger")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_events (
    event_id   TEXT PRIMARY KEY,
    sequence   INTEGER,
    timestamp  TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    session_id TEXT NOT NULL,
    tenant_id  TEXT NOT NULL DEFAULT 'default',
    prev_hash  TEXT NOT NULL DEFAULT '',
    signature  TEXT NOT NULL DEFAULT '',
    metadata   TEXT NOT NULL DEFAULT '{}'
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_events_session
    ON memory_events(session_id);

    CREATE INDEX IF NOT EXISTS idx_memory_events_tenant
        ON memory_events(tenant_id);

    CREATE INDEX IF NOT EXISTS idx_memory_events_tenant_sequence
        ON memory_events(tenant_id, sequence);
"""


class EventLedgerL3:
    """Immutable event sourcing ledger for cognitive memory.

    All writes go through SQLite WAL (via pre-configured aiosqlite
    connection) ensuring non-blocking, crash-safe persistence.
    """

    __slots__ = ("_conn", "_ready", "_last_hash_cache")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self._last_hash_cache: dict[str, str] = {}  # tenant_id -> last_hash

    async def ensure_table(self) -> None:
        """Create the events table if it doesn't exist (idempotent)."""
        if self._ready:
            return
        await self._conn.executescript(_CREATE_TABLE_SQL)
        await self._conn.executescript(_CREATE_INDEX_SQL)
        await self._ensure_sequence_column()
        await self._conn.commit()
        self._ready = True

    async def _ensure_sequence_column(self) -> None:
        """Backfill a stable append sequence for deterministic replay."""
        cursor = await self._conn.execute("PRAGMA table_info(memory_events)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "sequence" not in columns:
            await self._conn.execute("ALTER TABLE memory_events ADD COLUMN sequence INTEGER")
        await self._conn.execute(
            "UPDATE memory_events SET sequence = rowid WHERE sequence IS NULL"
        )

    async def _get_last_hash(self, tenant_id: str) -> str:
        """Fetch the signature of the last event for a tenant to continue the chain."""
        if tenant_id in self._last_hash_cache:
            return self._last_hash_cache[tenant_id]

        cursor = await self._conn.execute(
            """SELECT signature FROM memory_events
               WHERE tenant_id = ?
               ORDER BY sequence DESC, rowid DESC
               LIMIT 1""",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        last_hash = row[0] if row else "GENESIS"
        self._last_hash_cache[tenant_id] = last_hash
        return last_hash

    async def _event_exists(self, event_id: str) -> bool:
        """Check whether an event ID is already present in the ledger."""
        cursor = await self._conn.execute(
            "SELECT 1 FROM memory_events WHERE event_id = ? LIMIT 1",
            (event_id,),
        )
        return await cursor.fetchone() is not None

    @staticmethod
    def _compute_event_signature(event: MemoryEvent, prev_hash: str) -> str:
        """Compute the deterministic chain signature for a memory event."""
        content_hash = hashlib.sha3_256(event.content.encode()).hexdigest()
        payload = (
            f"{event.event_id}:{event.timestamp.isoformat()}:"
            f"{event.tenant_id}:{event.role}:{content_hash}:{prev_hash}"
        )
        return hashlib.sha3_256(payload.encode()).hexdigest()

    async def _next_sequence(self, tenant_id: str) -> int:
        """Return the next stable append sequence for a tenant."""
        cursor = await self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM memory_events WHERE tenant_id = ?",
            (tenant_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 1

    async def append_event(self, event: MemoryEvent) -> None:
        """Persist an event immutably. Fire-and-commit with SHA-3-256 integrity."""
        await self.ensure_table()
        if await self._event_exists(event.event_id):
            return

        expected_prev_hash = await self._get_last_hash(event.tenant_id)
        if event.signature:
            if event.prev_hash != expected_prev_hash:
                raise ValueError(
                    "Pre-signed memory event prev_hash does not match the current tenant chain head."
                )

            expected_signature = self._compute_event_signature(event, event.prev_hash)
            if event.signature != expected_signature:
                raise ValueError(
                    "Pre-signed memory event signature does not match the event payload."
                )
        else:
            signature = self._compute_event_signature(event, expected_prev_hash)

            # Update event model in-place (since it's a Pydantic model)
            # Using object.__setattr__ if the model is frozen (which it is)
            object.__setattr__(event, "prev_hash", expected_prev_hash)
            object.__setattr__(event, "signature", signature)

        sequence = await self._next_sequence(event.tenant_id)
        await self._conn.execute(
            """INSERT OR IGNORE INTO memory_events
               (event_id, sequence, timestamp, role, content, token_count,
                session_id, tenant_id, prev_hash, signature, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                sequence,
                event.timestamp.isoformat(),
                event.role,
                event.content,
                event.token_count,
                event.session_id,
                event.tenant_id,
                event.prev_hash,
                event.signature,
                json.dumps(event.metadata),
            ),
        )
        await self._conn.commit()
        self._last_hash_cache[event.tenant_id] = event.signature

    async def get_session_events(
        self,
        session_id: str,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryEvent]:
        """Retrieve events for a session in chronological order, scoped by tenant."""
        tenant_id = tenant_id or get_tenant_id()
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count,
                      session_id, tenant_id, prev_hash, signature, metadata
               FROM memory_events
               WHERE session_id = ? AND tenant_id = ?
               ORDER BY sequence ASC, rowid ASC
               LIMIT ?""",
            (session_id, tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]  # type: ignore[reportArgumentType]

    async def replay(self, tenant_id: str, limit: int = 1000) -> list[MemoryEvent]:
        """Replay events for a specific tenant in chronological order for state reconstruction."""
        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, token_count,
                      session_id, tenant_id, prev_hash, signature, metadata
               FROM memory_events
               WHERE tenant_id = ?
               ORDER BY sequence ASC, rowid ASC
               LIMIT ?""",
            (tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_event(row) for row in rows]  # type: ignore[reportArgumentType]

    async def count(self, tenant_id: str, session_id: str | None = None) -> int:
        """Count events for a tenant, optionally filtered by session."""
        await self.ensure_table()
        if session_id:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM memory_events WHERE tenant_id = ? AND session_id = ?",
                (tenant_id, session_id),
            )
        else:
            cursor = await self._conn.execute(
                "SELECT COUNT(*) FROM memory_events WHERE tenant_id = ?",
                (tenant_id,),
            )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def verify_chain(self, tenant_id: str) -> dict[str, Any]:
        """
        [GOVERNANCE] Deep cryptographic audit of the memory event chain.
        Recalculates every signature and verifies the back-pointers.
        """
        import hashlib

        await self.ensure_table()
        cursor = await self._conn.execute(
            """SELECT event_id, timestamp, role, content, tenant_id, prev_hash, signature
               FROM memory_events
               WHERE tenant_id = ?
               ORDER BY sequence ASC, rowid ASC""",
            (tenant_id,),
        )

        audit_log = []
        is_corrupt = False
        last_sig = "GENESIS"
        count = 0

        async for row in cursor:
            count += 1
            eid, ts, role, content, tid, prev_hash, sig = row

            # 1. Verify Hash Continuity
            if prev_hash != last_sig:
                audit_log.append(
                    f"DISCONTINUITY: Event {eid} expects prev={prev_hash} "
                    f"but actual last={last_sig}"
                )
                is_corrupt = True

            # 2. Verify Signature Integrity
            content_hash = hashlib.sha3_256(content.encode()).hexdigest()
            payload = f"{eid}:{ts}:{tid}:{role}:{content_hash}:{prev_hash}"
            expected_sig = hashlib.sha3_256(payload.encode()).hexdigest()

            if sig != expected_sig:
                audit_log.append(
                    f"TAMPER_DETECTED: Event {eid} has sig={sig} "
                    f"but content generates {expected_sig}"
                )
                is_corrupt = True

            last_sig = sig

        integrity = 1.0
        if is_corrupt and count > 0:
            integrity = (count - len(audit_log)) / count

        return {
            "tenant_id": tenant_id,
            "status": "VALID" if not is_corrupt else "CORRUPT",
            "events_audited": count,
            "integrity_score": integrity,
            "findings": audit_log or ["Memory event chain shows 100% integrity."],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _row_to_event(row: tuple) -> MemoryEvent:
    """Convert a database row to a MemoryEvent model."""
    raw_ts = row[1]
    ts = datetime.fromisoformat(raw_ts) if isinstance(raw_ts, str) else raw_ts
    return MemoryEvent(
        event_id=row[0],
        timestamp=ts,
        role=row[2],
        content=row[3],
        token_count=row[4],
        session_id=row[5],
        tenant_id=row[6],
        prev_hash=row[7],
        signature=row[8],
        metadata=json.loads(row[9]) if row[9] else {},
    )
