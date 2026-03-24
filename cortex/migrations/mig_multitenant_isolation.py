from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _pk_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in sorted(rows, key=lambda row: row[5]) if row[5] > 0]


def _migration_025_multitenant_isolation(conn: sqlite3.Connection) -> None:
    """Harden ledger and lock tables so tenant isolation is structural."""
    if _table_exists(conn, "merkle_roots"):
        merkle_columns = set(_column_names(conn, "merkle_roots"))
        if "tenant_id" not in merkle_columns:
            conn.execute(
                "ALTER TABLE merkle_roots ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
            )
            logger.info("[mig-025] Added merkle_roots.tenant_id")

    if _table_exists(conn, "lock_state"):
        pk_columns = _pk_columns(conn, "lock_state")
        if pk_columns != ["resource", "tenant_id"]:
            conn.execute("DROP TRIGGER IF EXISTS trg_lock_ttl_release")
            conn.execute("ALTER TABLE lock_state RENAME TO lock_state__old")
            conn.execute(
                """
                CREATE TABLE lock_state (
                    resource TEXT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    holder_agent TEXT,
                    acquired_at TEXT,
                    expires_at TEXT,
                    queue_depth INTEGER DEFAULT 0,
                    PRIMARY KEY (resource, tenant_id)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO lock_state (
                    resource,
                    tenant_id,
                    holder_agent,
                    acquired_at,
                    expires_at,
                    queue_depth
                )
                SELECT
                    resource,
                    COALESCE(tenant_id, 'default'),
                    holder_agent,
                    acquired_at,
                    expires_at,
                    COALESCE(queue_depth, 0)
                FROM lock_state__old
                """
            )
            conn.execute("DROP TABLE lock_state__old")
            logger.info("[mig-025] Rebuilt lock_state with tenant-aware primary key")

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_lock_intents_tenant_resource
            ON lock_intents(tenant_id, resource);
        CREATE INDEX IF NOT EXISTS idx_merkle_roots_tenant_range
            ON merkle_roots(tenant_id, tx_start_id, tx_end_id);

        DROP TRIGGER IF EXISTS trg_lock_ttl_release;
        CREATE TRIGGER trg_lock_ttl_release
        AFTER INSERT ON lock_intents
        BEGIN
            UPDATE lock_state
            SET holder_agent = NULL,
                acquired_at = NULL,
                expires_at = NULL,
                queue_depth = MAX(0, queue_depth - 1)
            WHERE resource = NEW.resource
              AND tenant_id = NEW.tenant_id
              AND expires_at IS NOT NULL
              AND expires_at < datetime('now');
        END;
        """
    )
    logger.info("[mig-025] Tenant isolation hardened for ledger and lock surfaces")
