from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex.migrations")


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migration_026_facts_contract(conn: sqlite3.Connection) -> None:
    """Reconcile the facts table with the runtime's canonical contract."""
    columns = _column_names(conn, "facts")

    if "tx_id" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN tx_id INTEGER REFERENCES transactions(id)")
        logger.info("[mig-026] Added facts.tx_id")

    if "cognitive_layer" not in columns:
        conn.execute(
            "ALTER TABLE facts ADD COLUMN cognitive_layer TEXT DEFAULT 'semantic' "
            "CHECK( cognitive_layer IN "
            "('working', 'episodic', 'semantic', 'relationship', 'emotional') )"
        )
        logger.info("[mig-026] Added facts.cognitive_layer")

    if "parent_decision_id" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN parent_decision_id INTEGER REFERENCES facts(id)")
        logger.info("[mig-026] Added facts.parent_decision_id")

    if "consensus_score" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN consensus_score REAL DEFAULT 0.0")
        logger.info("[mig-026] Added facts.consensus_score")

    if "last_accessed" not in columns:
        conn.execute("ALTER TABLE facts ADD COLUMN last_accessed TEXT")
        logger.info("[mig-026] Added facts.last_accessed")

    conn.execute(
        """
        UPDATE facts
        SET tx_id = COALESCE(
            tx_id,
            CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.tx_id') END
        )
        WHERE tx_id IS NULL
        """
    )
    conn.execute(
        """
        UPDATE facts
        SET consensus_score = COALESCE(
            consensus_score,
            CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.consensus_score') END,
            0.0
        )
        WHERE consensus_score IS NULL
        """
    )
    conn.execute(
        """
        UPDATE facts
        SET cognitive_layer = COALESCE(
            CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.cognitive_layer') END,
            NULLIF(cognitive_layer, ''),
            'semantic'
        )
        WHERE cognitive_layer IS NULL
            OR cognitive_layer = ''
            OR (
                cognitive_layer = 'semantic'
                AND json_valid(metadata)
                AND json_extract(metadata, '$.cognitive_layer') IS NOT NULL
            )
        """
    )
    conn.execute(
        """
        UPDATE facts
        SET parent_decision_id = COALESCE(
            parent_decision_id,
            CASE WHEN json_valid(metadata) THEN json_extract(metadata, '$.parent_decision_id') END
        )
        WHERE parent_decision_id IS NULL
        """
    )

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_facts_tx_id ON facts(tx_id);
        CREATE INDEX IF NOT EXISTS idx_facts_parent_decision ON facts(parent_decision_id);
        """
    )
    logger.info("[mig-026] Facts contract reconciled")
