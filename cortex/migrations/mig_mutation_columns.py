"""
Migration: mig_mutation_columns
Adds quarantined_at, quarantine_reason, and tombstoned_at to the facts table.
"""
import logging
import sqlite3

import aiosqlite

logger = logging.getLogger("cortex.migrations")

async def upgrade(conn: aiosqlite.Connection) -> None:
    for col, col_def in [
        ("quarantined_at", "TEXT"),
        ("quarantine_reason", "TEXT"),
        ("tombstoned_at", "TEXT"),
    ]:
        try:
            await conn.execute(f"ALTER TABLE facts ADD COLUMN {col} {col_def}")
        except (sqlite3.OperationalError, aiosqlite.Error) as e:
            if "duplicate column name" not in str(e).lower():
                raise
    logger.info("mig_mutation_columns: Added new ghost columns to facts table")

async def downgrade(conn: aiosqlite.Connection) -> None:
    for col in ["quarantined_at", "quarantine_reason", "tombstoned_at"]:
        try:
            await conn.execute(f"ALTER TABLE facts DROP COLUMN {col}")
        except (sqlite3.OperationalError, aiosqlite.Error) as e:
            logger.warning("mig_mutation_columns downgrade failed for %s: %s", col, e)
