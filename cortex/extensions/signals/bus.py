"""SQLite-backed signal bus used by the memory subsystem and telemetry."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
import collections

import aiosqlite
from cortex.extensions.signals.models import Signal, signal_from_row

__all__ = ["SignalBus", "AsyncSignalBus"]

logger = logging.getLogger("cortex.extensions.signals.bus")

# --- V7 DEEP-SCALE IN-MEMORY CACHE ---
# Zero-Copy Pub/Sub ring buffer para 10,000 agentes
_SWARM_RAM_BROKER = collections.deque(maxlen=100_000)
_GLOBAL_ID_SEQ = 0
# ------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL,
    project TEXT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    consumed_by TEXT NOT NULL DEFAULT '[]'
);
"""

_CREATE_INDEXES = """\
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
CREATE INDEX IF NOT EXISTS idx_signals_tenant ON signals(tenant_id);
"""


def _build_query(
    *,
    tenant_id: str = "default",
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    project: Optional[str] = None,
    unconsumed_by: Optional[str] = None,
    order: str = "ASC",
    limit: int = 50,
) -> tuple[str, list]:
    query = (
        "SELECT id, event_type, payload, source, project,"
        " created_at, consumed_by FROM signals WHERE tenant_id = ?"
    )
    params: list = [tenant_id]
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if source:
        query += " AND source = ?"
        params.append(source)
    if project:
        query += " AND project = ?"
        params.append(project)
    if unconsumed_by:
        query += " AND consumed_by NOT LIKE ?"
        params.append(f'%"{unconsumed_by}"%')
    query += f" ORDER BY rowid {order} LIMIT ?"
    params.append(limit)
    return query, params


class AsyncSignalBus:
    __slots__ = ("_conn", "_ready", "session_emitted", "session_errors")

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0

    async def ensure_table(self) -> None:
        if self._ready:
            return
        await self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)

        cursor = await self._conn.execute("PRAGMA table_info(signals)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "tenant_id" not in columns:
            await self._conn.execute(
                "ALTER TABLE signals ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_tenant ON signals(tenant_id)"
            )

        await self._conn.commit()
        self._ready = True

    async def emit(
        self,
        event_type: str,
        payload: Optional[dict] = None,
        *,
        source: str = "cli",
        project: Optional[str] = None,
        tenant_id: str = "default",
    ) -> int:
        global _GLOBAL_ID_SEQ
        _GLOBAL_ID_SEQ += 1
        sig_id = _GLOBAL_ID_SEQ

        # In-Memory Fast Path
        signal = Signal(
            id=sig_id,
            event_type=event_type,
            payload=payload or {},
            source=source,
            project=project,
            tenant_id=tenant_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            consumed_by=[],
        )
        _SWARM_RAM_BROKER.append(signal)
        self.session_emitted += 1

        # Fire-and-Forget a SQLite (Cold Storage)
        try:
            await self.ensure_table()
            sql = (
                "INSERT INTO signals "
                "(event_type, payload, source, project, tenant_id) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            await self._conn.execute(
                sql,
                (
                    event_type,
                    json.dumps(payload or {}, default=str),
                    source,
                    project,
                    tenant_id,
                ),
            )
            await self._conn.commit()
        except Exception as e:
            self.session_errors += 1
            logger.debug(f"Cold-Storage SQLite error (Signal RAM kept): {e}")

        return sig_id

    async def history(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Signal]:
        await self.ensure_table()
        query, params = _build_query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            order="DESC",
            limit=limit,
        )
        if since:
            query = query.replace(" ORDER BY", " AND created_at >= ? ORDER BY", 1)
            params.insert(-1, since.isoformat())
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [signal_from_row(tuple(row)) for row in rows]

    async def _query(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        unconsumed_by: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        query, params = _build_query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=unconsumed_by,
            limit=limit,
        )
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [signal_from_row(tuple(row)) for row in rows]

    async def poll(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        # Latency-Zero RAM Polling
        matches = []
        for sig in reversed(_SWARM_RAM_BROKER):  # LIFO fast scan
            if len(matches) >= limit:
                break
            if sig.tenant_id != tenant_id:
                continue
            if event_type and sig.event_type != event_type:
                continue
            if source and sig.source != source:
                continue
            if project and sig.project != project:
                continue
            if consumer in sig.consumed_by:
                continue

            sig.consumed_by.append(consumer)
            matches.append(sig)

        return matches

    async def peek(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        await self.ensure_table()
        return await self._query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

    async def stats(self, tenant_id: str = "default") -> dict:
        await self.ensure_table()
        result: dict = {
            "session_emitted": self.session_emitted,
            "session_errors": self.session_errors,
        }

        row = await (
            await self._conn.execute(
                "SELECT COUNT(*) FROM signals WHERE tenant_id = ?", (tenant_id,)
            )
        ).fetchone()
        result["total"] = row[0] if row else 0

        cursor = await self._conn.execute(
            """SELECT event_type, COUNT(*) FROM signals
               WHERE tenant_id = ? GROUP BY event_type ORDER BY COUNT(*) DESC""",
            (tenant_id,),
        )
        result["by_type"] = {r[0]: r[1] for r in await cursor.fetchall()}

        cursor = await self._conn.execute(
            """SELECT source, COUNT(*) FROM signals
               WHERE tenant_id = ? GROUP BY source ORDER BY COUNT(*) DESC""",
            (tenant_id,),
        )
        result["by_source"] = {r[0]: r[1] for r in await cursor.fetchall()}

        row = await (
            await self._conn.execute(
                "SELECT COUNT(*) FROM signals WHERE consumed_by = '[]' AND tenant_id = ?",
                (tenant_id,),
            )
        ).fetchone()
        result["unconsumed"] = row[0] if row else 0

        return result

    async def gc(self, max_age_days: int = 30, tenant_id: Optional[str] = None) -> int:
        await self.ensure_table()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()

        sql = "DELETE FROM signals WHERE consumed_by != '[]' AND created_at < ?"
        params: list = [cutoff]
        if tenant_id:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)

        cursor = await self._conn.execute(sql, tuple(params))
        await self._conn.commit()
        pruned = cursor.rowcount
        if pruned:
            logger.info(
                "GC: pruned %d consumed signal(s) older than %d days (%s)",
                pruned,
                max_age_days,
                f"tenant: {tenant_id}" if tenant_id else "all tenants",
            )
        return pruned


class SignalBus:
    __slots__ = ("_conn", "_ready", "session_emitted", "session_errors")

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0

    def ensure_table(self) -> None:
        if self._ready:
            return
        self._conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)

        cursor = self._conn.execute("PRAGMA table_info(signals)")
        columns = [row[1] for row in cursor.fetchall()]
        if "tenant_id" not in columns:
            self._conn.execute(
                "ALTER TABLE signals ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_tenant ON signals(tenant_id)"
            )

        self._conn.commit()
        self._ready = True

    def emit(
        self,
        event_type: str,
        payload: Optional[dict] = None,
        *,
        source: str = "cli",
        project: Optional[str] = None,
        tenant_id: str = "default",
    ) -> int:
        try:
            self.ensure_table()
            cursor = self._conn.execute(
                """INSERT INTO signals (event_type, payload, source, project, tenant_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    event_type,
                    json.dumps(payload or {}, default=str),
                    source,
                    project,
                    tenant_id,
                ),
            )
            self._conn.commit()
            signal_id = cursor.lastrowid
            logger.info(
                "Signal emitted: %s (#%d) from %s (tenant: %s)",
                event_type,
                signal_id,
                source,
                tenant_id,
            )
            self.session_emitted += 1
            return signal_id or 0
        except Exception:
            self.session_errors += 1
            raise

    def poll(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: str = "default",
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        signals = self._query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

        for sig in signals:
            new_consumed = sig.consumed_by + [consumer]
            self._conn.execute(
                "UPDATE signals SET consumed_by = ? WHERE id = ? AND tenant_id = ?",
                (json.dumps(new_consumed), sig.id, tenant_id),
            )
        if signals:
            self._conn.commit()
            logger.info(
                "Polled %d signal(s) as consumer '%s' (tenant: %s)",
                len(signals),
                consumer,
                tenant_id,
            )

        return signals

    def peek(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        consumer: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        return self._query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=consumer,
            limit=limit,
        )

    def history(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Signal]:
        self.ensure_table()
        query, params = _build_query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            order="DESC",
            limit=limit,
        )
        if since:
            query = query.replace(" ORDER BY", " AND created_at >= ? ORDER BY", 1)
            params.insert(-1, since.isoformat())
        cursor = self._conn.execute(query, params)
        return [signal_from_row(tuple(row)) for row in cursor.fetchall()]

    def stats(self, tenant_id: str = "default") -> dict:
        self.ensure_table()
        result: dict = {
            "session_emitted": self.session_emitted,
            "session_errors": self.session_errors,
        }

        row = self._conn.execute(
            "SELECT COUNT(*) FROM signals WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        result["total"] = row[0] if row else 0

        cursor = self._conn.execute(
            """SELECT event_type, COUNT(*) FROM signals
               WHERE tenant_id = ? GROUP BY event_type ORDER BY COUNT(*) DESC""",
            (tenant_id,),
        )
        result["by_type"] = {r[0]: r[1] for r in cursor.fetchall()}

        cursor = self._conn.execute(
            """SELECT source, COUNT(*) FROM signals
               WHERE tenant_id = ? GROUP BY source ORDER BY COUNT(*) DESC""",
            (tenant_id,),
        )
        result["by_source"] = {r[0]: r[1] for r in cursor.fetchall()}

        row = self._conn.execute(
            "SELECT COUNT(*) FROM signals WHERE consumed_by = '[]' AND tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        result["unconsumed"] = row[0] if row else 0

        return result

    def gc(self, max_age_days: int = 30, tenant_id: Optional[str] = None) -> int:
        self.ensure_table()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()

        sql = "DELETE FROM signals WHERE consumed_by != '[]' AND created_at < ?"
        params: list = [cutoff]
        if tenant_id:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)

        cursor = self._conn.execute(sql, tuple(params))
        self._conn.commit()
        pruned = cursor.rowcount
        if pruned:
            logger.info(
                "GC: pruned %d consumed signal(s) older than %d days (%s)",
                pruned,
                max_age_days,
                f"tenant: {tenant_id}" if tenant_id else "all tenants",
            )
        return pruned

    def _query(
        self,
        *,
        tenant_id: str = "default",
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        project: Optional[str] = None,
        unconsumed_by: Optional[str] = None,
        limit: int = 50,
    ) -> list[Signal]:
        query, params = _build_query(
            tenant_id=tenant_id,
            event_type=event_type,
            source=source,
            project=project,
            unconsumed_by=unconsumed_by,
            limit=limit,
        )
        cursor = self._conn.execute(query, params)
        return [signal_from_row(tuple(row)) for row in cursor.fetchall()]
