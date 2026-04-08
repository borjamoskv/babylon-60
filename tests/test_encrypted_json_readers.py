from __future__ import annotations

import asyncio
import sqlite3
import time
from unittest.mock import MagicMock

import aiosqlite
import pytest

from cortex.crypto.aes import CortexEncrypter, load_json_dict
from cortex.engine.reporter import SovereignReporter
from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.l2_hybrid_search import L2HybridSearch
from cortex.memory.models import CortexFactModel
from cortex.routes.telemetry import query_new_facts

TEST_MASTER_KEY = b"0" * 32


@pytest.fixture
def encrypter(monkeypatch: pytest.MonkeyPatch) -> CortexEncrypter:
    enc = CortexEncrypter(TEST_MASTER_KEY)
    monkeypatch.setattr("cortex.crypto.aes.get_default_encrypter", lambda: enc)
    monkeypatch.setattr("cortex.routes.telemetry.get_default_encrypter", lambda: enc)
    return enc


@pytest.mark.asyncio
async def test_load_json_dict_supports_encrypted_and_plaintext(encrypter: CortexEncrypter) -> None:
    encrypted = encrypter.encrypt_json({"secret": "value"}, tenant_id="tenant-a")

    assert load_json_dict(encrypted, tenant_id="tenant-a") == {"secret": "value"}
    assert load_json_dict('{"plain": true}', tenant_id="tenant-a") == {"plain": True}
    assert load_json_dict("not-json", tenant_id="tenant-a") == {}


@pytest.mark.asyncio
async def test_query_new_facts_decrypts_content_and_metadata(encrypter: CortexEncrypter) -> None:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            fact_type TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, fact_type, content, metadata) VALUES (?, ?, ?, ?, ?)",
        (
            1,
            "tenant-a",
            "human_mutation",
            encrypter.encrypt_str("decrypted content", tenant_id="tenant-a"),
            encrypter.encrypt_json({"kind": "mutation"}, tenant_id="tenant-a"),
        ),
    )
    await conn.commit()

    class _SessionCtx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _Engine:
        def session(self):
            return _SessionCtx()

    max_id, facts = await query_new_facts(_Engine(), 0, "human_mutation")

    assert max_id == 1
    assert facts == [
        {
            "fact_id": 1,
            "content": "decrypted content",
            "meta": {"kind": "mutation"},
        }
    ]
    await conn.close()


@pytest.mark.asyncio
async def test_reporter_fetches_encrypted_roi_metadata(encrypter: CortexEncrypter) -> None:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            fact_type TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    await conn.execute(
        "INSERT INTO facts (id, tenant_id, fact_type, source, metadata) VALUES (?, ?, ?, ?, ?)",
        (
            1,
            "tenant-a",
            "knowledge",
            "chronos-roi",
            encrypter.encrypt_json({"roi_ratio": 3.2}, tenant_id="tenant-a"),
        ),
    )
    await conn.commit()

    reporter = SovereignReporter(db_path=":memory:")
    history = await reporter._fetch_roi_history(conn)

    assert history == [{"roi_ratio": 3.2}]
    await conn.close()


@pytest.mark.asyncio
async def test_hdc_store_encrypts_metadata_and_preserves_toxic_lookup(
    encrypter: CortexEncrypter,
) -> None:
    store = object.__new__(HDCVectorStoreL2)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE hdc_facts_meta (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            content TEXT,
            timestamp REAL,
            is_diamond INTEGER,
            is_bridge INTEGER,
            confidence TEXT,
            success_rate REAL,
            metadata TEXT,
            fact_type TEXT
        )
        """
    )
    conn.execute(
        "CREATE TABLE hdc_vec_facts (rowid INTEGER PRIMARY KEY, embedding BLOB)"
    )
    conn.execute(
        "CREATE TABLE hdc_specular_vec_facts (rowid INTEGER PRIMARY KEY, embedding BLOB)"
    )

    object.__setattr__(store, "_encoder", MagicMock(dimension=4, encode_fact=lambda **_: [1, -1, 1, -1]))
    object.__setattr__(store, "_item_memory", MagicMock(save_codebook=lambda: None))
    object.__setattr__(store, "_db_path", ":memory:")
    object.__setattr__(store, "_conn", conn)
    object.__setattr__(store, "_lock", asyncio.Lock())
    object.__setattr__(store, "_ready", True)
    object.__setattr__(store, "_half_life", 7 * 24 * 3600)

    fact = CortexFactModel(
        id="hdc-toxic-1",
        tenant_id="tenant-a",
        project_id="project-a",
        content="counterexample violation",
        embedding=[1, 1, 1, 1],
        timestamp=time.time(),
        confidence="C5",
        metadata={"is_toxic": True, "secret": "sealed"},
    )
    await HDCVectorStoreL2.memorize(store, fact, fact_type="error")

    row = conn.execute("SELECT metadata FROM hdc_facts_meta WHERE id = ?", ("hdc-toxic-1",)).fetchone()
    assert row is not None
    assert row["metadata"].startswith(CortexEncrypter.PREFIX)
    assert load_json_dict(row["metadata"], tenant_id="tenant-a") == {
        "is_toxic": True,
        "secret": "sealed",
    }

    toxic_ids = await HDCVectorStoreL2.get_toxic_ids(store, "tenant-a", "project-a", limit=5)
    assert toxic_ids == ["hdc-toxic-1"]


def test_l2_hybrid_hydrate_supports_encrypted_metadata(encrypter: CortexEncrypter) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE facts_meta (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            content TEXT,
            timestamp REAL,
            is_diamond INTEGER,
            is_bridge INTEGER,
            confidence TEXT,
            cognitive_layer TEXT,
            metadata TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO facts_meta (
            id, tenant_id, project_id, content, timestamp,
            is_diamond, is_bridge, confidence, cognitive_layer, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "fact-1",
            "tenant-a",
            "project-a",
            "ranked result",
            123.0,
            0,
            0,
            "C4",
            "semantic",
            encrypter.encrypt_json({"channel": "hybrid"}, tenant_id="tenant-a"),
        ),
    )

    engine = L2HybridSearch(MagicMock())
    results = engine._hydrate(conn, [("fact-1", 0.75, ["vector", "fts"])])

    assert len(results) == 1
    assert results[0].metadata == {"channel": "hybrid"}
