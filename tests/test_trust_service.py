from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from cortex.services.trust import TrustService


def _setup_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                hash TEXT,
                project TEXT,
                tx_id INTEGER
            );
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL
            );
            """
        )


def test_verify_fact_chain_fails_closed_when_fact_has_no_transaction(tmp_path: Path) -> None:
    db_path = tmp_path / "trust.db"
    _setup_db(db_path)

    content = "fact without transaction"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO facts (content, hash, project, tx_id) VALUES (?, ?, ?, ?)",
            (content, hashlib.sha256(content.encode()).hexdigest(), "trust-proj", None),
        )

    result = TrustService(str(db_path)).verify_fact_chain(1)

    assert result.valid is False
    assert result.tx_id is None
    assert result.violation is not None
    assert "MISSING_TRANSACTION_LINK" in result.violation


def test_verify_fact_chain_succeeds_when_transaction_link_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "trust.db"
    _setup_db(db_path)

    content = "fact with transaction"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO transactions (timestamp) VALUES (?)",
            ("2026-04-14T00:00:00Z",),
        )
        tx_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO facts (content, hash, project, tx_id) VALUES (?, ?, ?, ?)",
            (content, content_hash, "trust-proj", tx_id),
        )

    result = TrustService(str(db_path)).verify_fact_chain(1)

    assert result.valid is True
    assert result.tx_id == tx_id
    assert result.violation is None
