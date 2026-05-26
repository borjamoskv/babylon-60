"""Unit tests for Sovereign Immutable Ledger — cortex/ledger/ledger_core.py."""

import json
import pytest
import sqlite3
import aiosqlite
from dataclasses import dataclass
from typing import Any
from cortex.ledger.ledger_core import MerkleTree, SemanticMerkleTree, SovereignLedger

def test_merkle_tree_basic():
    """Test Merkle Tree root generation and proofs."""
    leaves = ["a", "b", "c", "d"]
    tree = MerkleTree(leaves)
    root = tree.root_hash
    assert root is not None

    # Proof for index 0 ("a")
    proof = tree.get_proof(0)
    assert len(proof) == 2 # log2(4)
    assert MerkleTree.verify_proof("a", proof, root) is True
    assert MerkleTree.verify_proof("b", proof, root) is False

def test_merkle_tree_odd_leaves():
    """Test Merkle Tree with odd number of leaves (duplication)."""
    leaves = ["a", "b", "c"]
    tree = MerkleTree(leaves)
    root = tree.root_hash
    assert root is not None

    for i, leaf in enumerate(leaves):
        proof = tree.get_proof(i)
        assert MerkleTree.verify_proof(leaf, proof, root) is True

@dataclass
class MockFingerprint:
    hash: str
    embedding: list[float]

def mock_batch_fingerprint(contents, embedder=None):
    return [MockFingerprint(hash=str(hash(c)), embedding=[float(i) for i in range(10)]) for c in contents]

def mock_semantic_fingerprint(content, embedder=None):
    return MockFingerprint(hash=str(hash(content)), embedding=[float(i) for i in range(10)])

def test_semantic_merkle_tree(monkeypatch):
    """Test Semantic Merkle Tree integrity via mocked embeddings."""
    import cortex.ledger.ledger_core
    monkeypatch.setattr("cortex.engine.semantic_hash.batch_fingerprint", mock_batch_fingerprint)
    monkeypatch.setattr("cortex.engine.semantic_hash.semantic_fingerprint", mock_semantic_fingerprint)
    monkeypatch.setattr("cortex.engine.semantic_hash.cosine_similarity", lambda a, b: 1.0)

    contents = ["fact 1", "fact 2"]
    tree = SemanticMerkleTree(contents)

    assert tree.root_hash is not None

    # Verify content
    res = tree.verify_content(0, "fact 1 paraphrased")
    assert res["valid"] is True
    assert res["similarity"] == 1.0

@pytest.fixture
def sync_db():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()

def test_sovereign_ledger_sync_ops(sync_db):
    """Test synchronous SovereignLedger operations."""
    ledger = SovereignLedger(sync_db)

    # Record transaction
    h1 = ledger.record_transaction(project="P1", action="STORE", detail={"data": 1})
    assert h1 is not None

    # Verify it exists
    cursor = sync_db.execute("SELECT hash, prev_hash FROM transactions WHERE hash = ?", (h1,))
    row = cursor.fetchone()
    assert row[0] == h1
    assert row[1] == "GENESIS"

    # Record another
    h2 = ledger.record_transaction(project="P1", action="STORE", detail={"data": 2})
    assert h2 is not None

    cursor = sync_db.execute("SELECT prev_hash FROM transactions WHERE hash = ?", (h2,))
    assert cursor.fetchone()[0] == h1

@pytest.mark.asyncio
async def test_sovereign_ledger_async_ops():
    """Test asynchronous SovereignLedger operations."""
    async with aiosqlite.connect(":memory:") as db:
        # SovereignLedger expects an object it can use syncly in __init__ for schema
        # but for async it needs a proxy.
        # We can pass the aiosqlite connection directly as it's supported for _get_conn_proxy
        ledger = SovereignLedger(db)
        # Schema needs to be created. SovereignLedger.__init__ only does it for sync connections.
        # Let's manually trigger schema creation via a sync connection for the same :memory:
        # (Actually, SovereignLedger doesn't have an async schema init, it relies on _ensure_schema_sync)
        # We'll mock the _is_sync_connection to False and manually ensure schema if needed,
        # but SovereignLedger._get_conn_proxy works with aiosqlite.Connection.

        # We need the tables. Let's use a trick to run the sync schema init on a temp sync conn.
        sync_conn = sqlite3.connect(":memory:") # This won't work for the same memory db
        # Let's just manually run the schema on the async conn.
        await db.executescript("""
            CREATE TABLE transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project     TEXT NOT NULL,
                action      TEXT NOT NULL,
                detail      TEXT,
                prev_hash   TEXT NOT NULL,
                hash        TEXT NOT NULL UNIQUE,
                tenant_id   TEXT NOT NULL DEFAULT 'default',
                timestamp   TEXT NOT NULL
            );
            CREATE TABLE merkle_roots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id       TEXT NOT NULL DEFAULT '__global__',
                root_hash       TEXT NOT NULL,
                tx_start_id     INTEGER NOT NULL,
                tx_end_id       INTEGER NOT NULL,
                tx_count        INTEGER NOT NULL,
                signature       TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE integrity_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                check_type      TEXT NOT NULL,
                status          TEXT NOT NULL,
                details         TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT NOT NULL
            );
        """)

        h = await ledger.record_transaction_async(project="P_ASYNC", action="TEST", detail={"val": 42})
        assert h is not None

        audit = await ledger.audit_integrity_async()
        assert audit["valid"] is True
        assert audit["tx_count"] == 1

@pytest.mark.asyncio
async def test_ledger_tamper_detection():
    """Test audit_integrity_async detects tampering."""
    async with aiosqlite.connect(":memory:") as db:
        ledger = SovereignLedger(db)
        # Manual schema again
        await db.executescript("""
            CREATE TABLE transactions (id INTEGER PRIMARY KEY, project TEXT, action TEXT, detail TEXT, prev_hash TEXT, hash TEXT, tenant_id TEXT, timestamp TEXT);
            CREATE TABLE merkle_roots (id INTEGER PRIMARY KEY, tenant_id TEXT, root_hash TEXT, tx_start_id INTEGER, tx_end_id INTEGER, tx_count INTEGER, signature TEXT, created_at TEXT);
            CREATE TABLE integrity_checks (id INTEGER PRIMARY KEY, check_type TEXT, status TEXT, details TEXT, started_at TEXT, completed_at TEXT);
        """)

        await ledger.record_transaction_async(project="P1", action="A1")

        # Tamper with the hash
        await db.execute("UPDATE transactions SET hash = 'TAMPERED' WHERE id = 1")
        await db.commit()

        audit = await ledger.audit_integrity_async()
        assert audit["valid"] is False
        assert any(v["type"] == "TAMPER_DETECTED" for v in audit["violations"])
