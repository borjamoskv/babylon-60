# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Migration 019 — Signal Bus (L1 Consciousness Layer).

Adds the persistent signals table for cross-tool reactive communication.
"""

from __future__ import annotations

import sqlite3


def _migration_019_signal_bus(conn: sqlite3.Connection) -> None:
    """Create the signals table and indexes.

    NOTE: tenant_id is NOT in the original DDL here because this migration
    runs *after* mig-015 (tenant_unification) which dynamically adds
    tenant_id to every table that lacks it — including signals when it is
    created here for the first time on an existing DB.

    For *fresh* databases the canonical DDL in schema_extensions.CREATE_SIGNALS
    already includes tenant_id, so the two paths converge correctly.

    Migration-019 therefore intentionally omits tenant_id to avoid a
    duplicate-column error when mig-015 has already run on its own connection
    pass.  The idx_signals_tenant index is added by mig-015 critical_indices
    injection for the same reason — we add it here only as a belt-and-suspenders
    guard via CREATE INDEX IF NOT EXISTS (idempotent).
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id   TEXT NOT NULL DEFAULT 'default',
            event_type  TEXT NOT NULL,
            payload     TEXT NOT NULL DEFAULT '{}',
            source      TEXT NOT NULL,
            project     TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            consumed_by TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_signals_tenant ON signals(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
        CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
        CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
        CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
        CREATE INDEX IF NOT EXISTS idx_signals_tenant_project
            ON signals(tenant_id, project);
    """)
