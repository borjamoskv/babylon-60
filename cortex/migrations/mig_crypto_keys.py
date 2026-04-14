"""
CORTEX Migration v23 — Per-Fact Crypto Keys (GDPR Crypto-Shredding).

Creates the ``crypto_keys`` table that maps each fact to its unique
symmetric AES-256-GCM encryption key.  Shredding a fact means permanently
deleting its row from this table; the ciphertext stored in ``facts.content``
becomes mathematically irrecoverable, satisfying GDPR Art. 17 (Right to
Erasure) without touching the immutable hash chain.

Architecture note:
  - ``facts.content`` is encrypted with a random per-fact key (``v7_factenc:`` prefix).
  - ``crypto_keys.fact_key`` holds the raw 32-byte AES key for that fact.
  - The Merkle / transaction hash chain is computed over the *ciphertext*, so
    deleting the key row leaves chain integrity intact.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("cortex")


def _migration_023_crypto_keys(conn: sqlite3.Connection) -> None:
    """Add crypto_keys table for per-fact encryption-key management."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crypto_keys (
            fact_id    INTEGER PRIMARY KEY,
            tenant_id  TEXT    NOT NULL DEFAULT 'default',
            fact_key   BLOB    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_crypto_keys_tenant "
        "ON crypto_keys(tenant_id)"
    )
    logger.info("Migration 023: crypto_keys table ensured")
