from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from cortex.engine import CortexEngine
from cortex.migrations.core import run_migrations


def _facts_columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}


def _bootstrap_legacy_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        );
        INSERT INTO schema_version (version, description)
        VALUES (25, 'Legacy baseline without canonical facts columns');

        CREATE TABLE facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            tags TEXT NOT NULL DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            hash TEXT,
            valid_from TEXT,
            valid_until TEXT,
            source TEXT,
            confidence TEXT DEFAULT 'C3',
            tx_id INTEGER,
            consensus_score REAL DEFAULT 0.0,
            last_accessed TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_tombstoned INTEGER NOT NULL DEFAULT 0,
            is_quarantined INTEGER NOT NULL DEFAULT 0,
            quarantined_at TEXT,
            quarantine_reason TEXT,
            tombstoned_at TEXT
        );

        INSERT INTO facts (
            tenant_id, project, content, fact_type, tags, metadata, confidence, tx_id, created_at, updated_at
        )
        VALUES (
            'default',
            'legacy-project',
            'legacy-fact',
            'knowledge',
            '[]',
            '{"cognitive_layer":"working","parent_decision_id":7}',
            'C4',
            11,
            datetime('now'),
            datetime('now')
        );
        """
    )
    run_migrations(conn)

    columns = _facts_columns(conn)
    assert {"cognitive_layer", "parent_decision_id", "tx_id", "consensus_score", "last_accessed"} <= columns

    row = conn.execute(
        "SELECT cognitive_layer, parent_decision_id, tx_id FROM facts WHERE id = 1"
    ).fetchone()
    assert row == ("working", 7, 11)
    conn.close()


@pytest.mark.asyncio
async def test_migrated_db_matches_fresh_facts_contract(tmp_path: Path) -> None:
    os.environ["CORTEX_SKIP_EXERGY_VALIDATION"] = "1"
    db_path = tmp_path / "migrated-contract.db"
    _bootstrap_legacy_db(db_path)

    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    try:
        await engine.init_db()

        parent_id = await engine.store(
            project="legacy-project",
            content="parent decision after migration",
            fact_type="decision",
            source="test-suite",
        )
        child_id = await engine.store(
            project="legacy-project",
            content="child fact after migration",
            fact_type="knowledge",
            source="test-suite",
            meta={"cognitive_layer": "relationship"},
            parent_decision_id=parent_id,
        )

        child = await engine.get_fact(child_id, tenant_id="default")
        assert child is not None
        assert child.tx_id is not None
        assert child.cognitive_layer == "relationship"
        assert child.parent_decision_id == parent_id
    finally:
        await engine.close()
        os.environ.pop("CORTEX_SKIP_EXERGY_VALIDATION", None)
