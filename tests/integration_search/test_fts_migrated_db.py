from __future__ import annotations

import sqlite3
from pathlib import Path

from cortex.database.schema import get_all_schema
from cortex.migrations.core import run_migrations


def _apply_schema(conn: sqlite3.Connection) -> None:
    for stmt in get_all_schema():
        try:
            conn.executescript(stmt)
        except sqlite3.Error as exc:
            msg = str(exc).lower()
            if "vec0" in stmt or "no such module" in msg or "duplicate column" in msg:
                continue
            raise


def _bootstrap_legacy_fts_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    _apply_schema(conn)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now')),
            description TEXT
        )
    """)
    conn.execute("DELETE FROM schema_version")
    conn.execute(
        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
        (16, "Legacy trigger-based FTS baseline"),
    )

    conn.executescript("""
        DROP TRIGGER IF EXISTS facts_ai;
        DROP TRIGGER IF EXISTS facts_au;
        DROP TRIGGER IF EXISTS facts_ad;

        CREATE TRIGGER facts_ai AFTER INSERT ON facts BEGIN
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
        END;

        CREATE TRIGGER facts_au AFTER UPDATE ON facts BEGIN
            DELETE FROM facts_fts WHERE rowid = OLD.id;
            INSERT INTO facts_fts(rowid, content, project, tags, fact_type)
            VALUES (NEW.id, NEW.content, NEW.project, NEW.tags, NEW.fact_type);
        END;

        CREATE TRIGGER facts_ad AFTER DELETE ON facts BEGIN
            DELETE FROM facts_fts WHERE rowid = OLD.id;
        END;
    """)

    conn.execute(
        """
        INSERT INTO facts (
            tenant_id, project, content, fact_type, tags, metadata, hash,
            valid_from, source, confidence, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "default",
            "migrated-search",
            "legacy plaintext indexable fact",
            "knowledge",
            "[]",
            "{}",
            "plain-hash",
            "test-suite",
            "C4",
        ),
    )
    conn.execute(
        """
        INSERT INTO facts (
            tenant_id, project, content, fact_type, tags, metadata, hash,
            valid_from, source, confidence, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "default",
            "migrated-search",
            "v6_aesgcm:deadbeef",
            "knowledge",
            "[]",
            "{}",
            "cipher-hash",
            "test-suite",
            "C4",
        ),
    )
    conn.commit()

    pre_rows = conn.execute("SELECT rowid, content FROM facts_fts ORDER BY rowid").fetchall()
    assert pre_rows == [
        (1, "legacy plaintext indexable fact"),
        (2, "v6_aesgcm:deadbeef"),
    ]

    run_migrations(conn)

    triggers = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'trigger'
          AND sql IS NOT NULL
          AND (sql LIKE '%facts_fts%' OR name IN ('facts_ai', 'facts_au', 'facts_ad'))
        """
    ).fetchall()
    assert triggers == []

    rows = conn.execute("SELECT rowid, content FROM facts_fts ORDER BY rowid").fetchall()
    assert rows == [(1, "legacy plaintext indexable fact")]
    conn.close()


def test_migrated_db_rebuilds_fts_without_ciphertext_or_triggers(tmp_path: Path) -> None:
    _bootstrap_legacy_fts_db(tmp_path / "fts-migrated.db")
