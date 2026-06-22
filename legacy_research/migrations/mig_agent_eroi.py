# [C5-REAL] Exergy-Maximized
import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_031_agent_eroi(conn: sqlite3.Connection):
    """Implement subagent EROI and task reputation tracking table."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_tasks_eroi (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id        TEXT NOT NULL REFERENCES agents(id),
            task_type       TEXT NOT NULL,
            exergy_yield    REAL NOT NULL,
            entropy_paid    REAL NOT NULL,
            tokens_spent    INTEGER NOT NULL DEFAULT 0,
            eroi_score      REAL NOT NULL,
            status          TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_eroi_agent_task ON agent_tasks_eroi(agent_id, task_type);
    """)
    logger.info("Migration 031: Created 'agent_tasks_eroi' table and index")
