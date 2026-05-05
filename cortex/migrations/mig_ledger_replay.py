"""Migration 023 — Ledger origin replay protection.

# DOWNGRADE TARGET: 22

Rollback strategy:
    DROP TABLE ledger_origin_replay;

Dropping the table disables replay protection but does not mutate ledger_events
or any existing hash-chain payload. No data is rewritten or rehashed.

sqlite-vec impact: none.
"""

from __future__ import annotations

import sqlite3


def _migration_023_ledger_origin_replay(conn: sqlite3.Connection) -> None:
    """Create sidecar replay reservations for strict ledger origin signatures."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ledger_origin_replay (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id        TEXT NOT NULL DEFAULT 'default',
            actor_id         TEXT NOT NULL,
            key_id           TEXT NOT NULL,
            nonce            TEXT NOT NULL,
            event_id         TEXT NOT NULL,
            signed_at        TEXT NOT NULL,
            origin_signature TEXT NOT NULL,
            event_hash       TEXT,
            created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            UNIQUE(tenant_id, actor_id, key_id, nonce),
            UNIQUE(tenant_id, event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_ledger_origin_replay_nonce
            ON ledger_origin_replay(tenant_id, actor_id, key_id, nonce);
        CREATE INDEX IF NOT EXISTS idx_ledger_origin_replay_event
            ON ledger_origin_replay(tenant_id, event_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_origin_replay_signed_at
            ON ledger_origin_replay(signed_at);
    """)
