from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")


def _migration_027_lineage_tx(conn: sqlite3.Connection) -> None:
    """Backfill facts.tx_id from metadata first, then from the transaction ledger."""
    conn.execute(
        """
        UPDATE facts
        SET tx_id = CASE
            WHEN json_valid(metadata) THEN json_extract(metadata, '$.tx_id')
            ELSE tx_id
        END
        WHERE tx_id IS NULL
        """
    )

    conn.execute(
        """
        UPDATE facts
        SET tx_id = (
            SELECT t.id
            FROM transactions t
            WHERE t.tenant_id = facts.tenant_id
              AND t.project = facts.project
              AND t.timestamp <= COALESCE(facts.created_at, datetime('now'))
            ORDER BY t.timestamp DESC, t.id DESC
            LIMIT 1
        )
        WHERE tx_id IS NULL
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_tx_id ON facts(tx_id)")
    logger.info("[mig-027] Backfilled facts.tx_id from metadata/ledger and ensured index")
