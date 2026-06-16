# [C5-REAL] Exergy-Maximized
"""Immutable Ledger (Merkle) schema."""

CREATE_MERKLE_ROOTS = """
CREATE TABLE IF NOT EXISTS merkle_roots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT '__global__',
    root_hash       TEXT NOT NULL,
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    tx_count        INTEGER NOT NULL,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_INTEGRITY_CHECKS = """
CREATE TABLE IF NOT EXISTS integrity_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type      TEXT NOT NULL,
    status          TEXT NOT NULL,
    details         TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT NOT NULL
);
"""

CREATE_AUDIT_EXPORTS = """
CREATE TABLE IF NOT EXISTS audit_exports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type     TEXT NOT NULL,
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    exported_at     TEXT NOT NULL DEFAULT (datetime('now')),
    exported_by     TEXT NOT NULL
);
"""

SCHEMA = [
    CREATE_MERKLE_ROOTS,
    CREATE_INTEGRITY_CHECKS,
    CREATE_AUDIT_EXPORTS,
]
