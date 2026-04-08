from __future__ import annotations

import sqlite3

from cortex.migrations.mig_scaling_indexes import _migration_024_scaling_indexes


def test_migration_024_adds_scaling_indexes() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE enrichment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER,
            status TEXT NOT NULL,
            next_attempt_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL,
            parent_id INTEGER,
            edge_type TEXT NOT NULL,
            tenant_id TEXT NOT NULL
        );
        """
    )

    _migration_024_scaling_indexes(conn)

    tx_indexes = {row[1] for row in conn.execute("PRAGMA index_list(transactions)")}
    enrichment_indexes = {row[1] for row in conn.execute("PRAGMA index_list(enrichment_jobs)")}
    causal_indexes = {row[1] for row in conn.execute("PRAGMA index_list(causal_edges)")}

    assert "idx_tx_tenant_id_desc" in tx_indexes
    assert "idx_enrichment_jobs_status_created" in enrichment_indexes
    assert "idx_enrichment_jobs_status_retry_created" in enrichment_indexes
    assert "idx_causal_parent_edge_tenant" in causal_indexes
