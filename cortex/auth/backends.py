"""
CORTEX v6 — Authentication Backends.

Decouples authentication storage from the core AuthManager logic.
Supports SQLite (Local v5) and distributed cloud backends (v6).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Optional

import aiosqlite

# We keep the core dataclasses here to avoid circular imports if auth.py uses this
# But for now, let's assume those stay in auth.py and this file imports them if needed.
# Actually, it's better if backends.py doesn't depend on auth.py's internal classes.

logger = logging.getLogger(__name__)


class BaseAuthBackend(ABC):
    """Abstract base class for CORTEX authentication backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage schema (e.g., create tables)."""
        pass

    @abstractmethod
    async def get_key_by_hash(self, key_hash: str) -> Optional[dict[str, Any]]:
        """Retrieve an active API key by its hash."""
        pass

    @abstractmethod
    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        """Store a new API key. Returns the backend-specific unique ID."""
        pass

    @abstractmethod
    async def list_keys(self, tenant_id: Optional[str] = None) -> list[dict[str, Any]]:
        """List API keys, optionally filtered by tenant."""
        pass

    @abstractmethod
    async def revoke_key(self, key_id: int | str) -> bool:
        """Revoke (deactivate) an API key."""
        pass

    @abstractmethod
    async def update_last_used(self, key_id: int | str) -> None:
        """Update the last_used timestamp for a key."""
        pass


class SQLiteAuthBackend(BaseAuthBackend):
    """Async-first SQLite backend for CORTEX.

    Uses aiosqlite to prevent event loop blocking.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn_sync(self) -> sqlite3.Connection:
        from cortex.database.core import connect

        return connect(self.db_path)

    def initialize_sync(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        conn = self._get_conn_sync()
        try:
            conn.executescript(AUTH_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    async def initialize(self) -> None:
        from cortex.auth import AUTH_SCHEMA

        conn = await self._get_conn_async()
        try:
            await conn.executescript(AUTH_SCHEMA)
            await conn.commit()
        finally:
            await conn.close()

    async def _get_conn_async(self) -> aiosqlite.Connection:
        from cortex.database.core import connect_async

        return await connect_async(self.db_path)

    async def get_key_by_hash(self, key_hash: str) -> Optional[dict[str, Any]]:
        conn = await self._get_conn_async()
        try:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        finally:
            await conn.close()

    def get_key_by_hash_sync(self, key_hash: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn_sync()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        from cortex.auth import SQL_INSERT_KEY

        args = (name, key_hash, key_prefix, tenant_id, role, json.dumps(permissions), rate_limit)
        conn = await self._get_conn_async()
        try:
            cursor = await conn.execute(SQL_INSERT_KEY, args)
            await conn.commit()
            return cursor.lastrowid  # type: ignore[reportReturnType]
        finally:
            await conn.close()

    def store_key_sync(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        from cortex.auth import SQL_INSERT_KEY

        args = (name, key_hash, key_prefix, tenant_id, role, json.dumps(permissions), rate_limit)
        conn = self._get_conn_sync()
        try:
            cursor = conn.execute(SQL_INSERT_KEY, args)
            conn.commit()
            if cursor.lastrowid is None:
                msg = "SQLite did not return a rowid for the inserted API key"
                raise RuntimeError(msg)
            return int(cursor.lastrowid)
        finally:
            conn.close()

    async def list_keys(self, tenant_id: Optional[str] = None) -> list[dict[str, Any]]:
        conn = await self._get_conn_async()
        try:
            conn.row_factory = aiosqlite.Row
            if tenant_id:
                cursor = await conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cursor = await conn.execute("SELECT * FROM api_keys ORDER BY id DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    def list_keys_sync(self, tenant_id: Optional[str] = None) -> list[dict[str, Any]]:
        conn = self._get_conn_sync()
        try:
            conn.row_factory = sqlite3.Row
            if tenant_id:
                cursor = conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY id DESC",
                    (tenant_id,),
                )
            else:
                cursor = conn.execute("SELECT * FROM api_keys ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    async def revoke_key(self, key_id: int | str) -> bool:
        conn = await self._get_conn_async()
        try:
            cursor = await conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    def revoke_key_sync(self, key_id: int | str) -> bool:
        conn = self._get_conn_sync()
        try:
            cursor = conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = ?", (key_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    async def update_last_used(self, key_id: int | str) -> None:
        from datetime import datetime, timezone

        conn = await self._get_conn_async()
        try:
            await conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id),
            )
            await conn.commit()
        except (aiosqlite.Error, OSError) as e:
            logger.debug("Could not update last_used (async): %s", e)
        finally:
            await conn.close()

    def update_last_used_sync(self, key_id: int | str) -> None:
        from datetime import datetime, timezone

        conn = self._get_conn_sync()
        try:
            conn.execute(
                "UPDATE api_keys SET last_used = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id),
            )
            conn.commit()
        except (OSError, sqlite3.DatabaseError) as e:
            logger.debug("Could not update last_used (sync): %s", e)
        finally:
            conn.close()


class AlloyDBAuthBackend(BaseAuthBackend):
    """Distributed authentication backend for AlloyDB / PostgreSQL.

    Uses asyncpg for native asynchronous operations.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: Any | None = None
        self._pool_init_lock: asyncio.Lock | None = None

    async def _get_pool(self) -> Any:
        import asyncpg

        if self._pool is not None:
            return self._pool

        if self._pool_init_lock is None:
            self._pool_init_lock = asyncio.Lock()

        async with self._pool_init_lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(self.dsn)
        return self._pool

    async def initialize(self) -> None:
        from cortex.auth.schema import PG_AUTH_SCHEMA

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(PG_AUTH_SCHEMA)

    async def get_key_by_hash(self, key_hash: str) -> Optional[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key_hash = $1 AND is_active = 1",
                key_hash,
            )
            return dict(row) if row else None

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            key_id = await conn.fetchval(
                """
                INSERT INTO api_keys
                    (name, key_hash, key_prefix, tenant_id, role, permissions, rate_limit)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                name,
                key_hash,
                key_prefix,
                tenant_id,
                role,
                json.dumps(permissions),
                rate_limit,
            )
            return key_id

    async def list_keys(self, tenant_id: Optional[str] = None) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(
                    "SELECT * FROM api_keys WHERE tenant_id = $1 ORDER BY id DESC",
                    tenant_id,
                )
            else:
                rows = await conn.fetch("SELECT * FROM api_keys ORDER BY id DESC")
            return [dict(r) for r in rows]

    async def revoke_key(self, key_id: int | str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute("UPDATE api_keys SET is_active = 0 WHERE id = $1", key_id)
            # res is something like "UPDATE 1"
            return res.endswith("1")

    async def update_last_used(self, key_id: int | str) -> None:
        from datetime import datetime, timezone

        import asyncpg

        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE api_keys SET last_used = $1 WHERE id = $2",
                    datetime.now(timezone.utc).isoformat(),
                    key_id,
                )
        except (asyncpg.PostgresError, OSError) as e:
            logger.debug("Could not update last_used (async): %s", e)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
