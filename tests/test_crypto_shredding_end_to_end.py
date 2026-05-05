import json
import sqlite3

import aiosqlite
import pytest

from cortex.crypto.aes import CortexEncrypter
from cortex.crypto.shredder import CryptoShredder
from cortex.database.schema import CREATE_FACTS
from cortex.database.schema_extensions import CREATE_FACTS_FTS
from cortex.engine.fact_store_core import insert_fact_record
from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter

TEST_MASTER_KEY = b"2" * 32


async def _setup_fact_db(conn: aiosqlite.Connection) -> None:
    await conn.executescript("""
        CREATE TABLE causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_id INTEGER NOT NULL,
            parent_id INTEGER,
            signal_id INTEGER,
            edge_type TEXT NOT NULL DEFAULT 'triggered_by',
            project TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE fact_tags (
            fact_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            PRIMARY KEY (fact_id, tag)
        );
        CREATE TABLE fact_embeddings (
            fact_id INTEGER PRIMARY KEY,
            embedding BLOB,
            k INTEGER,
            distance REAL
        );
        CREATE TABLE enrichment_jobs (
            fact_id INTEGER PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    for stmt in CREATE_FACTS.strip().split(";"):
        s = stmt.strip()
        if s:
            await conn.execute(s + ";")
    await conn.executescript(CREATE_FACTS_FTS)
    await conn.commit()


def _setup_fact_db_sync(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            content TEXT NOT NULL,
            fact_type TEXT NOT NULL DEFAULT 'knowledge',
            metadata TEXT DEFAULT '{}',
            hash TEXT,
            valid_until TEXT,
            source TEXT,
            confidence TEXT DEFAULT 'C3',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_tombstoned INTEGER NOT NULL DEFAULT 0,
            tags TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS fact_embeddings (
            fact_id INTEGER PRIMARY KEY,
            embedding BLOB
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(content, project, tags, fact_type, tenant_id);
        CREATE TABLE IF NOT EXISTS enrichment_jobs (
            fact_id INTEGER PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()


@pytest.fixture
def encrypter() -> CortexEncrypter:
    return CortexEncrypter(TEST_MASTER_KEY)


@pytest.mark.asyncio
async def test_crypto_shred_fact_redacts_payload_and_indexes(monkeypatch, encrypter):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)

    conn = await aiosqlite.connect(":memory:")
    await _setup_fact_db(conn)

    fact_id = await insert_fact_record(
        conn,
        tenant_id="default",
        project="gdpr",
        content="alice@example.com visited Madrid branch",
        fact_type="knowledge",
        tags=["customer", "retail"],
        confidence="C5",
        ts=None,
        source="user:alice@example.com",
        meta={"subject_ref": "customer:alice"},
        tx_id=None,
    )
    await conn.execute(
        "INSERT OR REPLACE INTO fact_embeddings (fact_id, embedding, k, distance) VALUES (?, ?, ?, ?)",
        (fact_id, b"vec", 1, 0.0),
    )
    await conn.commit()

    async with conn.execute("SELECT content FROM facts WHERE id = ?", (fact_id,)) as cursor:
        row = await cursor.fetchone()
    assert row[0].startswith(encrypter.PREFIX)
    assert "alice@example.com" not in row[0]

    shredder = CryptoShredder(conn)
    result = await shredder.shred_fact_async(fact_id, shredded_by="dpo")
    assert result.success

    async with conn.execute(
        "SELECT content, metadata, source, tags, is_tombstoned FROM facts WHERE id = ?",
        (fact_id,),
    ) as cursor:
        fact_row = await cursor.fetchone()

    assert fact_row[0] == "CORTEX_ERASURE_TOMBSTONE"
    assert fact_row[2] == "subject-erased"
    assert fact_row[3] == "[]"
    assert fact_row[4] == 1

    tombstone_meta = json.loads(fact_row[1])
    assert tombstone_meta["erasure_status"] == "shredded"
    assert tombstone_meta["tombstone_reason"] == "gdpr_erasure"
    assert "alice@example.com" not in fact_row[1]

    async with conn.execute("SELECT COUNT(*) FROM facts_fts WHERE rowid = ?", (fact_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0
    async with conn.execute(
        "SELECT COUNT(*) FROM fact_embeddings WHERE fact_id = ?",
        (fact_id,),
    ) as cursor:
        assert (await cursor.fetchone())[0] == 0
    async with conn.execute(
        "SELECT COUNT(*) FROM enrichment_jobs WHERE fact_id = ?",
        (fact_id,),
    ) as cursor:
        assert (await cursor.fetchone())[0] == 0

    await conn.close()


@pytest.mark.asyncio
async def test_crypto_shred_by_source_is_subject_scoped(monkeypatch, encrypter):
    monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: encrypter)

    conn = await aiosqlite.connect(":memory:")
    await _setup_fact_db(conn)

    alice_one = await insert_fact_record(
        conn,
        tenant_id="default",
        project="gdpr",
        content="alice@example.com first fact",
        fact_type="knowledge",
        tags=["customer"],
        confidence="C5",
        ts=None,
        source="user:alice@example.com",
        meta={"subject_ref": "customer:alice"},
        tx_id=None,
    )
    alice_two = await insert_fact_record(
        conn,
        tenant_id="default",
        project="gdpr",
        content="alice@example.com second fact",
        fact_type="knowledge",
        tags=["customer"],
        confidence="C5",
        ts=None,
        source="user:alice@example.com",
        meta={"subject_ref": "customer:alice"},
        tx_id=None,
    )
    bob_one = await insert_fact_record(
        conn,
        tenant_id="default",
        project="gdpr",
        content="bob@example.com retained fact",
        fact_type="knowledge",
        tags=["customer"],
        confidence="C5",
        ts=None,
        source="user:bob@example.com",
        meta={"subject_ref": "customer:bob"},
        tx_id=None,
    )
    await conn.executemany(
        "INSERT OR REPLACE INTO fact_embeddings (fact_id, embedding, k, distance) VALUES (?, ?, ?, ?)",
        [(alice_one, b"vec", 1, 0.0), (alice_two, b"vec", 1, 0.0), (bob_one, b"vec", 1, 0.0)],
    )
    await conn.commit()

    shredder = CryptoShredder(conn)
    batch = await shredder.shred_by_source("user:alice@example.com", shredded_by="dpo")

    assert batch.total_requested == 2
    assert batch.shredded == 2
    assert batch.failed == 0

    async with conn.execute(
        "SELECT id, content, source, is_tombstoned FROM facts ORDER BY id"
    ) as cursor:
        rows = await cursor.fetchall()

    erased_rows = {row[0]: row for row in rows if row[0] in {alice_one, alice_two}}
    for row in erased_rows.values():
        assert row[1] == "CORTEX_ERASURE_TOMBSTONE"
        assert row[2] == "subject-erased"
        assert row[3] == 1

    retained_row = next(row for row in rows if row[0] == bob_one)
    assert retained_row[1].startswith(encrypter.PREFIX)
    assert retained_row[2] == "user:bob@example.com"
    assert retained_row[3] == 0

    await conn.close()


def test_crypto_shred_preserves_ledger_continuity(tmp_path):
    db_path = tmp_path / "crypto_shred_ledger.db"

    store = LedgerStore(str(db_path))
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)

    target = ActionTarget(app="Test")
    result = ActionResult(ok=True, latency_ms=5)
    for idx in range(3):
        writer.append(
            LedgerEvent.new(
                tool="cli",
                actor="tester",
                action=f"fact-{idx}",
                target=target,
                result=result,
                metadata={"project": "gdpr"},
            )
        )

    before = verifier.verify_chain()
    assert before["valid"]

    conn = sqlite3.connect(db_path)
    _setup_fact_db_sync(conn)
    conn.execute(
        "INSERT INTO facts (id, tenant_id, project, content, source, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "default", "gdpr", "secret payload", "user:alice@example.com", '{"subject_ref":"alice"}'),
    )
    conn.execute("INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)", (1, b"vec"))
    conn.execute(
        "INSERT INTO facts_fts (rowid, content, project, tags, fact_type, tenant_id) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "secret payload", "gdpr", "[]", "knowledge", "default"),
    )
    conn.commit()

    shredder = CryptoShredder(conn)
    shred = shredder.shred_fact(1, shredded_by="dpo")
    assert shred.success

    after = verifier.verify_chain()
    assert after["valid"]
    assert after["checked_events"] == before["checked_events"]

    conn.close()
