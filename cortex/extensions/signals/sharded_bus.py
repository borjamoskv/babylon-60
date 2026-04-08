"""
Sharded Signal Bus for CORTEX-SWARM-10K.
Eliminates lock contention by routing messages to specific SQLite DB shards
based on hash(sender/receiver) mod NUM_SHARDS.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from cortex import config
from cortex.extensions.signals.bus import _CREATE_INDEXES, _CREATE_TABLE, _build_query
from cortex.extensions.signals.models import Signal, signal_from_row
from cortex.guards.url_guard import SafeTransport

__all__ = ["ShardedDurableSignalBus", "ShardedAsyncSignalBus"]

logger = logging.getLogger("cortex.extensions.signals.sharded_bus")

NUM_SHARDS = getattr(config, "SWARM_SHARD_COUNT", 16)


class ShardedDurableSignalBus:
    """Durable sharded signal bus avoiding SQLite lock contention."""

    __slots__ = (
        "_base_dir",
        "_shards",
        "_ready",
        "session_emitted",
        "session_errors",
        "num_shards",
    )

    def __init__(self, base_dir: Path | str, num_shards: int = NUM_SHARDS) -> None:
        self._base_dir = self._resolve_base_dir(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._shards: dict[int, aiosqlite.Connection] = {}
        self._ready = False
        self.session_emitted = 0
        self.session_errors = 0
        self.num_shards = num_shards

    @staticmethod
    def _resolve_base_dir(base_dir: Path | str) -> Path:
        """Normalize file-like inputs into a directory usable for shard DBs."""
        candidate = Path(base_dir)
        if candidate.exists() and candidate.is_file():
            return candidate.parent / f"{candidate.name}.shards"
        if candidate.suffix:
            return candidate.parent / f"{candidate.name}.shards"
        return candidate

    def _get_shard_index(self, routing_key: str) -> int:
        h = hashlib.sha256(routing_key.encode("utf-8")).hexdigest()
        return int(h, 16) % self.num_shards

    async def initialize(self) -> None:
        """Initialize all shard connections and create tables."""
        if self._ready:
            return

        for i in range(self.num_shards):
            db_path = self._base_dir / f"swarm_shard_{i:03d}.db"
            conn = await aiosqlite.connect(db_path)
            await conn.executescript(_CREATE_TABLE + _CREATE_INDEXES)
            await conn.commit()
            self._shards[i] = conn

        self._ready = True

    async def close(self) -> None:
        """Close all shard connections."""
        for conn in self._shards.values():
            await conn.close()
        self._shards.clear()
        self._ready = False

    async def emit(
        self,
        event_type: str,
        payload: dict | None = None,
        *,
        source: str = "cli",
        project: str | None = None,
        tenant_id: str = "default",
        routing_key: str | None = None,
    ) -> int:
        if not self._ready:
            await self.initialize()

        # SSRF Protection: Validate any URLs in the payload
        if payload:
            for k, v in payload.items():
                if isinstance(v, str) and (k.endswith("_url") or "callback" in k):
                    SafeTransport.validate(v)

        rkey = routing_key or source
        shard_idx = self._get_shard_index(rkey)
        conn = self._shards[shard_idx]

        try:
            cursor = await conn.execute(
                "INSERT INTO signals "
                "(event_type, payload, source, project, tenant_id) VALUES (?, ?, ?, ?, ?)",
                (
                    event_type,
                    json.dumps(payload or {}, default=str),
                    source,
                    project,
                    tenant_id,
                ),
            )
            await conn.commit()
            self.session_emitted += 1
            return cursor.lastrowid or 0
        except Exception:
            self.session_errors += 1
            raise

    async def history(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        tenant_id: str = "default",
        since: datetime | None = None,
        limit: int = 50,
        routing_key: str | None = None,
    ) -> list[Signal]:
        if not self._ready:
            await self.initialize()

        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            tenant_id=tenant_id,
            order="DESC",
            limit=limit,
        )
        if since:
            query = query.replace(" ORDER BY", " AND created_at >= ? ORDER BY", 1)
            params.insert(-1, since.isoformat())

        if routing_key:
            shard_idx = self._get_shard_index(routing_key)
            conns = [self._shards[shard_idx]]
        else:
            conns = list(self._shards.values())

        async def fetch_rows(conn):
            cursor = await conn.execute(query, params)
            return await cursor.fetchall()

        async def safe_fetch(conn):
            return await asyncio.wait_for(fetch_rows(conn), timeout=5.0)

        all_results = await asyncio.gather(
            *(safe_fetch(c) for c in conns), return_exceptions=True
        )

        all_signals = []
        for rows in all_results:
            if isinstance(rows, Exception):
                logger.warning("Timeout or error in history shard fetch: %s", rows)
                continue
            all_signals.extend([signal_from_row(tuple(row)) for row in rows])

        all_signals.sort(key=lambda x: x.created_at, reverse=True)
        return all_signals[:limit]

    async def poll(
        self,
        *,
        event_type: str | None = None,
        source: str | None = None,
        project: str | None = None,
        tenant_id: str = "default",
        consumer: str = "default",
        limit: int = 50,
        routing_key: str | None = None,
    ) -> list[Signal]:
        if not self._ready:
            await self.initialize()

        query, params = _build_query(
            event_type=event_type,
            source=source,
            project=project,
            tenant_id=tenant_id,
            unconsumed_by=consumer,
            limit=limit,
        )

        shard_indices = (
            [self._get_shard_index(routing_key)] if routing_key else range(self.num_shards)
        )

        async def fetch_candidates(idx: int):
            conn = self._shards[idx]
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return idx, rows

        async def safe_fetch_candidates(idx: int):
            return await asyncio.wait_for(fetch_candidates(idx), timeout=5.0)

        # O(1) Cluster polling
        raw_results = await asyncio.gather(
            *(safe_fetch_candidates(idx) for idx in shard_indices), return_exceptions=True
        )
        results = [r for r in raw_results if not isinstance(r, Exception)]

        all_candidate_signals = []
        for idx, rows in results:
            for r in rows:
                all_candidate_signals.append((idx, signal_from_row(tuple(r))))

        # Sort globally to prevent starvation on higher shard indices (True Queue FIFO behavior)
        all_candidate_signals.sort(key=lambda pair: pair[1].created_at)
        selected_pairs = all_candidate_signals[:limit]

        polled_signals = []
        updates_by_shard = {}

        for idx, sig in selected_pairs:
            new_consumed = sig.consumed_by + [consumer]
            updates_by_shard.setdefault(idx, []).append((json.dumps(new_consumed), sig.id, tenant_id))
            polled_signals.append(sig)

        async def update_shard(idx: int, updates: list):
            conn = self._shards[idx]
            await conn.executemany(
                "UPDATE signals SET consumed_by = ? WHERE id = ? AND tenant_id = ?",
                updates,
            )
            await conn.commit()

        async def safe_update_shard(idx: int, updates: list):
            return await asyncio.wait_for(update_shard(idx, updates), timeout=5.0)

        if updates_by_shard:
            await asyncio.gather(
                *(
                    safe_update_shard(idx, updates)
                    for idx, updates in updates_by_shard.items()
                ),
                return_exceptions=True,
            )

        return polled_signals

    async def gc(self, max_age_days: int = 30, tenant_id: str | None = None) -> int:
        """Shannon Compaction: Auto-purge stale messages across all shards."""
        if not self._ready:
            await self.initialize()

        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        total_pruned = 0

        query = "DELETE FROM signals WHERE consumed_by != '[]' AND created_at < ?"
        params = [cutoff]
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)

        async def remove_from_shard(conn):
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount

        async def safe_remove_from_shard(conn):
            return await asyncio.wait_for(remove_from_shard(conn), timeout=5.0)

        raw_results = await asyncio.gather(
            *(safe_remove_from_shard(c) for c in self._shards.values()),
            return_exceptions=True,
        )
        results = [r for r in raw_results if not isinstance(r, Exception)]
        total_pruned = sum(results)

        if total_pruned:
            logger.info(
                "Sharded GC: pruned %d consumed signal(s) older than %d days",
                total_pruned,
                max_age_days,
            )

        return total_pruned


# Backward-compatible alias for the legacy sharded durable bus name.
ShardedAsyncSignalBus = ShardedDurableSignalBus
