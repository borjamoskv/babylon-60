from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from cortex.migrations import mig_fts
from cortex.migrations.mig_base import (
    _migration_001_add_updated_at,
    _migration_002_add_indexes,
    _migration_004_vector_index,
    _migration_005_fts5_setup,
)
from cortex.migrations.mig_hash import _migration_016_add_fact_hash
from cortex.migrations.mig_tenant import _migration_015_tenant_unification


@pytest.fixture
def conn() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    try:
        yield db
    finally:
        db.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _indexes(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }


def test_base_migrations_add_updated_at_indexes_pruned_embeddings_and_fts(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            project TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            valid_until TEXT
        );
    """)

    _migration_001_add_updated_at(conn)
    _migration_001_add_updated_at(conn)
    _migration_002_add_indexes(conn)
    _migration_004_vector_index(conn)
    _migration_005_fts5_setup(conn)

    assert "updated_at" in _columns(conn, "facts")
    assert _indexes(conn) >= {
        "idx_facts_project_active",
        "idx_facts_type",
        "idx_facts_created",
        "idx_pruned_at",
    }
    assert _columns(conn, "pruned_embeddings") >= {"fact_id", "hash", "dimension", "pruned_at"}
    assert _columns(conn, "facts_fts") >= {"content", "project", "tags", "fact_type"}


def test_hash_migration_adds_hash_column_and_tenant_scoped_partial_index(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            valid_until TEXT
        );
    """)

    _migration_016_add_fact_hash(conn)
    _migration_016_add_fact_hash(conn)

    assert "hash" in _columns(conn, "facts")
    assert "idx_facts_hash" in _indexes(conn)


def test_tenant_unification_adds_tenant_columns_and_skips_fts_tables(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript("""
        CREATE TABLE facts (id INTEGER PRIMARY KEY, content TEXT);
        CREATE TABLE sessions (id INTEGER PRIMARY KEY);
        CREATE VIRTUAL TABLE facts_fts USING fts5(content);
    """)

    _migration_015_tenant_unification(conn)

    assert "tenant_id" in _columns(conn, "facts")
    assert "tenant_id" in _columns(conn, "sessions")
    assert "tenant_id" not in _columns(conn, "facts_fts")
    assert {"idx_facts_tenant", "idx_sess_tenant"}.issubset(_indexes(conn))


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        (None, False),
        ({}, False),
        ({"allow_plaintext_fts": True}, True),
        ({"allow_plaintext_fts": False}, False),
        ({"allow_plaintext_fts": True, "privacy_flagged": True}, False),
    ],
)
def test_allows_plaintext_fts_requires_explicit_allow_without_privacy_flag(
    meta: dict[str, Any] | None, expected: bool
) -> None:
    assert mig_fts._allows_plaintext_fts(meta) is expected


def test_fts_decouple_repopulates_only_explicitly_allowed_plaintext_rows(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeEncrypter:
        def decrypt_json(self, raw: str, *, tenant_id: str) -> dict[str, Any]:
            if raw == "allow":
                return {"allow_plaintext_fts": True}
            if raw == "private":
                return {"allow_plaintext_fts": True, "privacy_flagged": True}
            if raw == "broken":
                raise ValueError("bad metadata")
            return {}

        def decrypt_str(self, value: str, *, tenant_id: str) -> str:
            return f"plain:{tenant_id}:{value}"

    monkeypatch.setattr(mig_fts, "get_default_encrypter", lambda: FakeEncrypter())
    conn.executescript("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            project TEXT NOT NULL,
            tags TEXT,
            fact_type TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            metadata TEXT,
            valid_until TEXT
        );
        CREATE VIRTUAL TABLE facts_fts USING fts5(content);
    """)
    conn.executemany(
        """
        INSERT INTO facts
            (id, content, project, tags, fact_type, tenant_id, metadata, valid_until)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "alpha", "p", "t", "knowledge", "tenant-a", "allow", None),
            (2, "beta", "p", "t", "knowledge", "tenant-a", "deny", None),
            (3, "gamma", "p", "t", "knowledge", "tenant-a", "private", None),
            (4, "delta", "p", "t", "knowledge", "tenant-a", "broken", None),
            (5, "expired", "p", "t", "knowledge", "tenant-a", "allow", "2026-01-01"),
        ],
    )

    mig_fts._migration_017_fts_decouple(conn)

    rows = conn.execute("SELECT rowid, content, project, tags, fact_type FROM facts_fts").fetchall()
    assert rows == [(1, "plain:tenant-a:alpha", "p", "t", "knowledge")]
