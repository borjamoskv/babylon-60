from __future__ import annotations

import sqlite3
from pathlib import Path

import aiosqlite
import pytest

from cortex.migrations.core import run_migrations
from cortex.search.text import text_search


class _FakeEnc:
    def decrypt_str(self, value: str, **_: object) -> str:
        return value

    def decrypt_json(self, value: object, **_: object):
        import json

        return json.loads(str(value))


def _bootstrap_migrated_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        );
        INSERT INTO schema_version (version, description)
        VALUES (26, 'Pre-lineage tx backfill baseline');

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            prev_hash TEXT,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

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
            cognitive_layer TEXT DEFAULT 'semantic',
            parent_decision_id INTEGER,
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

        CREATE VIRTUAL TABLE facts_fts USING fts5(content, project, tags, fact_type);

        INSERT INTO facts (
            tenant_id, project, content, fact_type, tags, metadata, hash, confidence, tx_id, created_at, updated_at
        )
        VALUES (
            'default',
            'legacy-search',
            'legacy hash lineage fact',
            'knowledge',
            '[]',
            '{"tx_id":41}',
            'fact-hash-legacy',
            'C4',
            NULL,
            datetime('now'),
            datetime('now')
        );

        INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
        VALUES (1, 'legacy hash lineage fact', 'legacy-search', '[]', 'knowledge');
        """
    )
    run_migrations(conn)

    row = conn.execute("SELECT tx_id, hash FROM facts WHERE id = 1").fetchone()
    assert row == (41, "fact-hash-legacy")
    conn.close()


@pytest.mark.asyncio
async def test_search_hash_does_not_depend_on_transaction_join(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: _FakeEnc())

    db_path = tmp_path / "lineage-migrated.db"
    _bootstrap_migrated_db(db_path)

    conn = await aiosqlite.connect(db_path)
    try:
        results = await text_search(
            conn,
            "legacy lineage",
            tenant_id="default",
            project="legacy-search",
            limit=5,
        )

        assert len(results) == 1
        assert results[0].tx_id == 41
        assert results[0].hash == "fact-hash-legacy"
    finally:
        await conn.close()
