"""Migration 023 — Schema Consolidation (Ghost Column Resolution).

Promotes ghost columns discovered during the 2026-03-24 audit:
- facts: last_accessed TEXT, consensus_score REAL
- agents: alignment_hits INTEGER, alignment_misses INTEGER, base_reputation REAL
- lock_intents: tenant_id TEXT
- lock_state: tenant_id TEXT

All operations use ALTER TABLE ADD COLUMN with IF NOT EXISTS semantics
(SQLite 3.35+) or try/except for older engines.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")

_COLUMNS_TO_ADD: list[tuple[str, str, str]] = [
    # (table, column_name, column_def)
    ("facts", "last_accessed", "TEXT"),
    ("facts", "consensus_score", "REAL DEFAULT 0.0"),
    ("agents", "alignment_hits", "INTEGER NOT NULL DEFAULT 0"),
    ("agents", "alignment_misses", "INTEGER NOT NULL DEFAULT 0"),
    ("agents", "base_reputation", "REAL NOT NULL DEFAULT 0.5"),
    ("lock_intents", "tenant_id", "TEXT NOT NULL DEFAULT 'default'"),
    ("lock_state", "tenant_id", "TEXT NOT NULL DEFAULT 'default'"),
]


def _migration_023_schema_consolidation(conn: sqlite3.Connection) -> None:
    """Add all ghost columns to existing databases."""
    for table, column, col_def in _COLUMNS_TO_ADD:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            logger.info("[mig-023] Added %s.%s", table, column)
        except Exception:  # noqa: BLE001 — column already exists
            logger.debug("[mig-023] Column %s.%s already exists, skipping", table, column)
