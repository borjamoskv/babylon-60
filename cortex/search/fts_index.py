"""Manual FTS synchronization helpers.

`facts_fts` is a standalone plaintext index. It must never be synchronized
through SQL triggers because `facts.content` may be encrypted at rest.
"""

from __future__ import annotations

import logging
import sqlite3

import aiosqlite

from cortex.crypto.aes import CortexEncrypter

logger = logging.getLogger("cortex.search.fts")

V6_PREFIX = CortexEncrypter.PREFIX


def plaintext_for_fts(content: str, stored_content: str) -> str | None:
    """Return searchable plaintext only when the stored fact is already plaintext."""
    if stored_content != content:
        return None
    return content


def plaintext_from_stored_content(stored_content: str | None) -> str | None:
    """Best-effort policy for migrated rows when only stored content is available."""
    if not stored_content or str(stored_content).startswith(V6_PREFIX):
        return None
    return str(stored_content)


async def replace_fact_fts_async(
    conn: aiosqlite.Connection,
    fact_id: int,
    *,
    plaintext: str | None,
    project: str,
    tags_json: str,
    fact_type: str,
) -> bool:
    """Replace a fact's FTS row using the canonical manual indexing policy."""
    try:
        await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        if plaintext is None:
            return False
        await conn.execute(
            "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (fact_id, plaintext, project, tags_json, fact_type),
        )
        return True
    except (sqlite3.Error, aiosqlite.Error) as exc:
        logger.warning("Failed to sync FTS row for fact %d: %s", fact_id, exc)
        return False


async def remove_fact_fts_async(conn: aiosqlite.Connection, fact_id: int) -> bool:
    """Delete a fact's FTS row. Safe even when the FTS table is unavailable."""
    try:
        await conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        return True
    except (sqlite3.Error, aiosqlite.Error) as exc:
        logger.warning("Failed to remove FTS row for fact %d: %s", fact_id, exc)
        return False


def replace_fact_fts_sync(
    conn: sqlite3.Connection,
    fact_id: int,
    *,
    plaintext: str | None,
    project: str,
    tags_json: str,
    fact_type: str,
) -> bool:
    """Sync variant for migrations and one-off maintenance scripts."""
    try:
        conn.execute("DELETE FROM facts_fts WHERE rowid = ?", (fact_id,))
        if plaintext is None:
            return False
        conn.execute(
            "INSERT INTO facts_fts(rowid, content, project, tags, fact_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (fact_id, plaintext, project, tags_json, fact_type),
        )
        return True
    except sqlite3.Error as exc:
        logger.warning("Failed to sync FTS row for fact %d during migration: %s", fact_id, exc)
        return False
