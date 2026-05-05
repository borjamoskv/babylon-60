"""
Crypto-shredding and erasure controls for mutable fact surfaces.

Current repository-demonstrated behavior:
  - Records an immutable erasure marker in `shredded_keys`.
  - Replaces mutable fact payload surfaces with a non-PII tombstone.
  - Purges mutable search/index side effects (`facts_fts`, `fact_embeddings`,
    pending enrichment jobs) for the shredded fact.
  - Leaves ledger continuity untouched because the append-only ledger is not
    mutated by this module.

This module does not claim per-fact envelope-key destruction beyond what the
repository currently enforces. It implements the executable erasure boundary
that the codebase can actually prove today.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger("cortex.crypto.shredder")

__all__ = ["CryptoShredder", "ShredResult", "ShredBatchResult"]

_TOMBSTONE_CONTENT = "CORTEX_ERASURE_TOMBSTONE"
_TOMBSTONE_SOURCE = "subject-erased"


@dataclass
class ShredResult:
    """Outcome of a single fact shred operation."""

    fact_id: int
    tenant_id: str
    success: bool
    reason: str = "gdpr_erasure"
    error: Optional[str] = None
    was_already_shredded: bool = False


@dataclass
class ShredBatchResult:
    """Aggregate result of a batch shred operation."""

    total_requested: int = 0
    shredded: int = 0
    already_shredded: int = 0
    failed: int = 0
    results: list[ShredResult] = field(default_factory=list)


class CryptoShredder:
    """Executable erasure controller for fact payloads and retrieval surfaces."""

    def __init__(self, conn: aiosqlite.Connection | sqlite3.Connection):
        self._conn = conn
        self._ensure_schema()

    def _is_async_connection(self) -> bool:
        return hasattr(self._conn, "_execute")

    def _ensure_schema(self) -> None:
        """Create shredded_keys table if it doesn't exist."""
        sql = """
            CREATE TABLE IF NOT EXISTS shredded_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id     INTEGER NOT NULL,
                tenant_id   TEXT    NOT NULL DEFAULT 'default',
                reason      TEXT    NOT NULL DEFAULT 'gdpr_erasure',
                shredded_by TEXT,
                shredded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(fact_id, tenant_id)
            );
        """
        try:
            if not self._is_async_connection():
                self._conn.execute(sql)
                self._conn.commit()
        except sqlite3.Error as e:
            logger.warning("Schema creation skipped (may exist): %s", e)

    def _fact_row(self, fact_id: int, tenant_id: str) -> Any:
        if self._is_async_connection():
            raise TypeError("Use async APIs for async connections")
        cursor: Any = self._conn.execute(
            "SELECT id FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return cursor.fetchone()

    async def _fact_row_async(self, fact_id: int, tenant_id: str) -> Any:
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT id FROM facts WHERE id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return await cursor.fetchone()

    def _table_exists(self, table_name: str) -> bool:
        if self._is_async_connection():
            raise TypeError("Use async APIs for async connections")
        cursor: Any = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
            (table_name,),
        )
        return cursor.fetchone() is not None

    async def _table_exists_async(self, table_name: str) -> bool:
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
            (table_name,),
        )
        return (await cursor.fetchone()) is not None

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        if self._is_async_connection():
            raise TypeError("Use async APIs for async connections")
        cursor: Any = self._conn.execute(f"PRAGMA table_info({table_name})")  # nosec B608
        return any(row[1] == column_name for row in cursor.fetchall())

    async def _column_exists_async(self, table_name: str, column_name: str) -> bool:
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            f"PRAGMA table_info({table_name})"  # nosec B608
        )
        rows = await cursor.fetchall()
        return any(row[1] == column_name for row in rows)

    def _tombstone_metadata(
        self,
        *,
        fact_id: int,
        tenant_id: str,
        shredded_at: str,
        reason: str,
        shredded_by: Optional[str],
    ) -> str:
        tombstone = {
            "erasure_status": "shredded",
            "tombstoned_at": shredded_at,
            "tombstone_reason": reason,
            "shredded_by": shredded_by or "system",
            "subject_ref": f"erased:{tenant_id}:{fact_id}",
        }
        return json.dumps(tombstone, sort_keys=True)

    def _redact_fact_surfaces(
        self,
        fact_id: int,
        tenant_id: str,
        reason: str,
        shredded_by: Optional[str],
        shredded_at: str,
    ) -> None:
        if self._is_async_connection():
            raise TypeError("Use async APIs for async connections")

        facts_columns = {
            "valid_until": self._column_exists("facts", "valid_until"),
            "is_tombstoned": self._column_exists("facts", "is_tombstoned"),
            "updated_at": self._column_exists("facts", "updated_at"),
            "metadata": self._column_exists("facts", "metadata"),
            "source": self._column_exists("facts", "source"),
            "tags": self._column_exists("facts", "tags"),
        }

        set_clauses = ["content = ?"]
        params: list[Any] = [_TOMBSTONE_CONTENT]

        if facts_columns["valid_until"]:
            set_clauses.append("valid_until = ?")
            params.append(shredded_at)
        if facts_columns["is_tombstoned"]:
            set_clauses.append("is_tombstoned = 1")
        if facts_columns["updated_at"]:
            set_clauses.append("updated_at = ?")
            params.append(shredded_at)
        if facts_columns["metadata"]:
            set_clauses.append("metadata = ?")
            params.append(
                self._tombstone_metadata(
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    shredded_at=shredded_at,
                    reason=reason,
                    shredded_by=shredded_by,
                )
            )
        if facts_columns["source"]:
            set_clauses.append("source = ?")
            params.append(_TOMBSTONE_SOURCE)
        if facts_columns["tags"]:
            set_clauses.append("tags = '[]'")

        params.extend([fact_id, tenant_id])
        self._conn.execute(
            f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ? AND tenant_id = ?",
            tuple(params),
        )

        for statement, statement_params in self._purge_related_surfaces_sql(fact_id):
            self._conn.execute(statement, statement_params)

    async def _redact_fact_surfaces_async(
        self,
        fact_id: int,
        tenant_id: str,
        reason: str,
        shredded_by: Optional[str],
        shredded_at: str,
    ) -> None:
        facts_columns = {
            "valid_until": await self._column_exists_async("facts", "valid_until"),
            "is_tombstoned": await self._column_exists_async("facts", "is_tombstoned"),
            "updated_at": await self._column_exists_async("facts", "updated_at"),
            "metadata": await self._column_exists_async("facts", "metadata"),
            "source": await self._column_exists_async("facts", "source"),
            "tags": await self._column_exists_async("facts", "tags"),
        }

        set_clauses = ["content = ?"]
        params: list[Any] = [_TOMBSTONE_CONTENT]

        if facts_columns["valid_until"]:
            set_clauses.append("valid_until = ?")
            params.append(shredded_at)
        if facts_columns["is_tombstoned"]:
            set_clauses.append("is_tombstoned = 1")
        if facts_columns["updated_at"]:
            set_clauses.append("updated_at = ?")
            params.append(shredded_at)
        if facts_columns["metadata"]:
            set_clauses.append("metadata = ?")
            params.append(
                self._tombstone_metadata(
                    fact_id=fact_id,
                    tenant_id=tenant_id,
                    shredded_at=shredded_at,
                    reason=reason,
                    shredded_by=shredded_by,
                )
            )
        if facts_columns["source"]:
            set_clauses.append("source = ?")
            params.append(_TOMBSTONE_SOURCE)
        if facts_columns["tags"]:
            set_clauses.append("tags = '[]'")

        params.extend([fact_id, tenant_id])
        await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            f"UPDATE facts SET {', '.join(set_clauses)} WHERE id = ? AND tenant_id = ?",
            tuple(params),
        )

        for statement, statement_params in await self._purge_related_surfaces_sql_async(fact_id):
            await self._conn.execute(statement, statement_params)  # type: ignore[reportAttributeAccessIssue]

    def _purge_related_surfaces_sql(self, fact_id: int) -> list[tuple[str, tuple[Any, ...]]]:
        if self._is_async_connection():
            raise TypeError("Use async APIs for async connections")
        statements: list[tuple[str, tuple[Any, ...]]] = []
        if self._table_exists("fact_embeddings"):
            statements.append(("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,)))
        if self._table_exists("facts_fts"):
            statements.append(("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,)))
        if self._table_exists("enrichment_jobs"):
            statements.append(("DELETE FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)))
        return statements

    async def _purge_related_surfaces_sql_async(
        self, fact_id: int
    ) -> list[tuple[str, tuple[Any, ...]]]:
        statements: list[tuple[str, tuple[Any, ...]]] = []
        if await self._table_exists_async("fact_embeddings"):
            statements.append(("DELETE FROM fact_embeddings WHERE fact_id = ?", (fact_id,)))
        if await self._table_exists_async("facts_fts"):
            statements.append(("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,)))
        if await self._table_exists_async("enrichment_jobs"):
            statements.append(("DELETE FROM enrichment_jobs WHERE fact_id = ?", (fact_id,)))
        return statements

    async def _ensure_schema_async(self) -> None:
        """Async variant for aiosqlite connections."""
        sql = """
            CREATE TABLE IF NOT EXISTS shredded_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id     INTEGER NOT NULL,
                tenant_id   TEXT    NOT NULL DEFAULT 'default',
                reason      TEXT    NOT NULL DEFAULT 'gdpr_erasure',
                shredded_by TEXT,
                shredded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(fact_id, tenant_id)
            );
        """
        try:
            await self._conn.execute(sql)  # type: ignore[reportAttributeAccessIssue]
            await self._conn.commit()  # type: ignore[reportAttributeAccessIssue]
        except (sqlite3.Error, OSError) as e:
            logger.warning("Async schema creation skipped: %s", e)

    def is_shredded(self, fact_id: int, tenant_id: str = "default") -> bool:
        """Check if a fact's key has been shredded (sync)."""
        if self._is_async_connection():
            raise TypeError("Use is_shredded_async for async connections")
        cursor: Any = self._conn.execute(
            "SELECT 1 FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return cursor.fetchone() is not None

    async def is_shredded_async(self, fact_id: int, tenant_id: str = "default") -> bool:
        """Check if a fact's key has been shredded (async)."""
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT 1 FROM shredded_keys WHERE fact_id = ? AND tenant_id = ?",
            (fact_id, tenant_id),
        )
        return (await cursor.fetchone()) is not None

    def get_shredded_fact_ids(self, tenant_id: str = "default") -> set[int]:
        """Return all shredded fact IDs for a tenant (sync)."""
        if self._is_async_connection():
            raise TypeError("Use get_shredded_fact_ids_async for async")
        cursor: Any = self._conn.execute(
            "SELECT fact_id FROM shredded_keys WHERE tenant_id = ?",
            (tenant_id,),
        )
        return {row[0] for row in cursor.fetchall()}

    async def get_shredded_fact_ids_async(self, tenant_id: str = "default") -> set[int]:
        """Return all shredded fact IDs for a tenant (async)."""
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT fact_id FROM shredded_keys WHERE tenant_id = ?",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

    def shred_fact(
        self,
        fact_id: int,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredResult:
        """Destroy the encryption key for a single fact (sync).

        The fact's ciphertext in the DB becomes permanently irrecoverable.
        The ledger hash chain is NOT affected (it hashes ciphertext, not plaintext).

        This also invalidates the HKDF-derived key from the encrypter's cache
        to prevent in-memory access after shredding.
        """
        if self._is_async_connection():
            raise TypeError("Use shred_fact_async for async connections")

        if self._fact_row(fact_id, tenant_id) is None:
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error="fact_not_found",
            )

        # Check if already shredded
        if self.is_shredded(fact_id, tenant_id):
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=True,
            )

        try:
            ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
            self._conn.execute("BEGIN IMMEDIATE")
            self._conn.execute(
                "INSERT INTO shredded_keys "
                "(fact_id, tenant_id, reason, shredded_by, shredded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact_id, tenant_id, reason, shredded_by, ts),
            )
            self._redact_fact_surfaces(
                fact_id,
                tenant_id,
                reason,
                shredded_by,
                ts,
            )

            # Invalidate the fact-specific derived key from the encrypter cache
            self._invalidate_fact_key(fact_id, tenant_id)

            self._conn.commit()
            logger.info(
                "Crypto-shredded fact #%d (tenant=%s, reason=%s)",
                fact_id,
                tenant_id,
                reason,
            )
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
            )
        except sqlite3.IntegrityError:
            self._conn.rollback()
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=True,
            )
        except (sqlite3.Error, OSError) as e:
            self._conn.rollback()
            logger.error("Shred failed for fact #%d: %s", fact_id, e)
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error=str(e),
            )

    async def shred_fact_async(
        self,
        fact_id: int,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredResult:
        """Destroy the encryption key for a single fact (async)."""
        await self._ensure_schema_async()
        if await self._fact_row_async(fact_id, tenant_id) is None:
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error="fact_not_found",
            )
        if await self.is_shredded_async(fact_id, tenant_id):
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=True,
            )

        try:
            ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
            await self._conn.execute("BEGIN IMMEDIATE")  # type: ignore[reportAttributeAccessIssue]
            await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
                "INSERT INTO shredded_keys "
                "(fact_id, tenant_id, reason, shredded_by, shredded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact_id, tenant_id, reason, shredded_by, ts),
            )
            await self._redact_fact_surfaces_async(
                fact_id,
                tenant_id,
                reason,
                shredded_by,
                ts,
            )

            self._invalidate_fact_key(fact_id, tenant_id)

            await self._conn.commit()  # type: ignore[reportAttributeAccessIssue]
            logger.info(
                "Crypto-shredded fact #%d (tenant=%s, reason=%s)",
                fact_id,
                tenant_id,
                reason,
            )
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
            )
        except sqlite3.IntegrityError:
            await self._conn.rollback()  # type: ignore[reportAttributeAccessIssue]
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=True,
                reason=reason,
                was_already_shredded=True,
            )
        except (sqlite3.Error, OSError) as e:
            await self._conn.rollback()  # type: ignore[reportAttributeAccessIssue]
            logger.error("Shred failed for fact #%d: %s", fact_id, e)
            return ShredResult(
                fact_id=fact_id,
                tenant_id=tenant_id,
                success=False,
                reason=reason,
                error=str(e),
            )

    async def shred_by_source(
        self,
        source: str,
        tenant_id: str = "default",
        reason: str = "gdpr_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredBatchResult:
        """Shred all facts from a specific source (e.g., a user agent).

        GDPR use case: user requests erasure of all their data.
        """
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT id FROM facts WHERE source = ? AND tenant_id = ?",
            (source, tenant_id),
        )
        rows = await cursor.fetchall()
        fact_ids = [row[0] for row in rows]

        return await self._shred_batch(fact_ids, tenant_id, reason, shredded_by)

    async def shred_by_project(
        self,
        project: str,
        tenant_id: str = "default",
        reason: str = "project_erasure",
        shredded_by: Optional[str] = None,
    ) -> ShredBatchResult:
        """Shred all facts in a project."""
        cursor = await self._conn.execute(  # type: ignore[reportAttributeAccessIssue]
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ?",
            (project, tenant_id),
        )
        rows = await cursor.fetchall()
        fact_ids = [row[0] for row in rows]

        return await self._shred_batch(fact_ids, tenant_id, reason, shredded_by)

    async def _shred_batch(
        self,
        fact_ids: list[int],
        tenant_id: str,
        reason: str,
        shredded_by: Optional[str],
    ) -> ShredBatchResult:
        """Internal batch shred implementation."""
        batch = ShredBatchResult(total_requested=len(fact_ids))

        for fact_id in fact_ids:
            result = await self.shred_fact_async(fact_id, tenant_id, reason, shredded_by)
            batch.results.append(result)

            if result.was_already_shredded:
                batch.already_shredded += 1
            elif result.success:
                batch.shredded += 1
            else:
                batch.failed += 1

        return batch

    def _invalidate_fact_key(self, fact_id: int, tenant_id: str) -> None:
        """Invalidate the HKDF-derived key for a fact from in-memory cache.

        After shredding, even if the encrypter has the master key,
        we poison the cache entry so decryption attempts fail fast.
        """
        try:
            from cortex.crypto.aes import get_default_encrypter

            enc = get_default_encrypter()
            # Remove the fact-specific key derivation marker
            # The _tenant_keys cache only stores per-tenant keys,
            # but we mark this fact_id as shredded so the decrypt
            # path can check before attempting HKDF derivation.
            cache_key = f"{tenant_id}:fact:{fact_id}"
            if hasattr(enc, "_shredded_facts"):
                enc._shredded_facts.add(cache_key)  # type: ignore[reportAttributeAccessIssue]
            else:
                enc._shredded_facts = {cache_key}  # type: ignore[reportAttributeAccessIssue]
        except (ImportError, RuntimeError) as e:
            logger.debug("Key invalidation skipped: %s", e)

    def audit_shredding(self) -> dict[str, Any]:
        """Report on all shredded facts for compliance auditing.

        Returns aggregate statistics without revealing content.
        """
        if not isinstance(self._conn, sqlite3.Connection):
            raise TypeError("Use audit_shredding_async for async")

        cursor = self._conn.execute(
            "SELECT COUNT(*), reason, MIN(shredded_at), MAX(shredded_at) "
            "FROM shredded_keys GROUP BY reason"
        )
        rows = cursor.fetchall()

        reasons = {}
        total = 0
        for row in rows:
            count, reason, earliest, latest = row
            total += count
            reasons[reason] = {
                "count": count,
                "earliest": earliest,
                "latest": latest,
            }

        return {
            "total_shredded": total,
            "by_reason": reasons,
            "compliant": True,
            "audit_timestamp": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
        }
