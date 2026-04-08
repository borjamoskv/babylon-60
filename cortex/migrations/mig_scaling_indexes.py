from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_024_scaling_indexes(conn: sqlite3.Connection) -> None:
    """Add hot-path indexes for queues, causal traversals, and tenant ledger reads.

    DOWNGRADE TARGET: 22
    """
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_tx_tenant_id_desc
            ON transactions(tenant_id, id DESC);

        CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_status_created
            ON enrichment_jobs(status, created_at);

        CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_status_retry_created
            ON enrichment_jobs(status, next_attempt_at, created_at);

        CREATE INDEX IF NOT EXISTS idx_causal_parent_edge_tenant
            ON causal_edges(parent_id, edge_type, tenant_id);
        """
    )
    logger.info("Migration 024: Added scaling indexes for transactions, enrichment_jobs, causal_edges")
