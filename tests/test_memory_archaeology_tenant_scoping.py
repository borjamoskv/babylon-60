from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from cortex.memory.memory_archaeology import MemoryArchaeologist


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _embedding_blob(*values: float) -> bytes:
    return np.array(values, dtype=np.float32).tobytes()


def _make_archaeologist(
    *,
    l3_conn: sqlite3.Connection,
    l2_conn: sqlite3.Connection,
    store: AsyncMock | None = None,
) -> MemoryArchaeologist:
    engine = SimpleNamespace(
        _get_sync_conn=lambda: l3_conn,
        memory=SimpleNamespace(_l2=SimpleNamespace(_get_conn=lambda: l2_conn)),
        store=store or AsyncMock(return_value="new-fact"),
    )
    return MemoryArchaeologist(engine)


def test_fetch_active_facts_filters_by_tenant() -> None:
    l3_conn = _connect()
    l3_conn.execute(
        """
        CREATE TABLE facts (
            id TEXT,
            tenant_id TEXT,
            project TEXT,
            content TEXT,
            parent_decision_id TEXT,
            is_tombstoned INTEGER,
            fact_type TEXT
        )
        """
    )
    l3_conn.executemany(
        "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("a1", "tenant-a", "proj", "alpha", None, 0, "knowledge"),
            ("b1", "tenant-b", "proj", "beta", None, 0, "knowledge"),
            ("a2", "tenant-a", "proj", "ghost", None, 0, "ghost"),
            ("a3", "tenant-a", "proj", "old", None, 1, "knowledge"),
        ],
    )

    archaeologist = _make_archaeologist(l3_conn=l3_conn, l2_conn=_connect())

    facts = archaeologist._fetch_active_facts("proj", "tenant-a")

    assert list(facts) == ["a1"]
    assert facts["a1"]["content"] == "alpha"


def test_extract_vectors_filters_l2_rows_by_tenant_even_with_duplicate_ids() -> None:
    l2_conn = _connect()
    l2_conn.execute(
        """
        CREATE TABLE facts_meta (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT,
            tenant_id TEXT,
            project_id TEXT,
            parent_decision_id TEXT
        )
        """
    )
    l2_conn.execute("CREATE TABLE vec_facts (rowid INTEGER PRIMARY KEY, embedding BLOB)")

    rowid_a = l2_conn.execute(
        "INSERT INTO facts_meta (id, tenant_id, project_id, parent_decision_id) VALUES (?, ?, ?, ?)",
        ("shared", "tenant-a", "proj", None),
    ).lastrowid
    rowid_b = l2_conn.execute(
        "INSERT INTO facts_meta (id, tenant_id, project_id, parent_decision_id) VALUES (?, ?, ?, ?)",
        ("shared", "tenant-b", "proj", None),
    ).lastrowid
    l2_conn.executemany(
        "INSERT INTO vec_facts (rowid, embedding) VALUES (?, ?)",
        [
            (rowid_a, _embedding_blob(1.0, 0.0)),
            (rowid_b, _embedding_blob(0.0, 2.0)),
        ],
    )

    archaeologist = _make_archaeologist(l3_conn=_connect(), l2_conn=l2_conn)
    l3_map = {"shared": {"content": "tenant-a fact", "parent_decision_id": None}}

    facts, vecs = archaeologist._extract_vectors("proj", "tenant-a", l3_map)

    assert [fact["id"] for fact in facts] == ["shared"]
    assert vecs is not None
    assert vecs.shape == (1, 2)
    assert vecs[0].tolist() == pytest.approx([1.0, 0.0])


@pytest.mark.asyncio
async def test_apply_db_updates_scopes_store_and_reparenting_to_tenant() -> None:
    l3_conn = _connect()
    l3_conn.execute(
        """
        CREATE TABLE facts (
            id TEXT,
            tenant_id TEXT,
            project TEXT,
            parent_decision_id TEXT,
            is_tombstoned INTEGER DEFAULT 0,
            valid_until TEXT
        )
        """
    )
    l3_conn.executemany(
        "INSERT INTO facts (id, tenant_id, project, parent_decision_id, is_tombstoned, valid_until) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("old-1", "tenant-a", "proj", None, 0, None),
            ("old-2", "tenant-a", "proj", None, 0, None),
            ("old-1", "tenant-b", "proj", None, 0, None),
            ("child-a", "tenant-a", "proj", "old-1", 0, None),
            ("child-b", "tenant-b", "proj", "old-1", 0, None),
        ],
    )

    l2_conn = _connect()
    l2_conn.execute(
        """
        CREATE TABLE facts_meta (
            id TEXT,
            tenant_id TEXT,
            parent_decision_id TEXT
        )
        """
    )
    l2_conn.execute("CREATE TABLE vec_facts (rowid INTEGER PRIMARY KEY, embedding BLOB)")
    l2_conn.executemany(
        "INSERT INTO facts_meta (id, tenant_id, parent_decision_id) VALUES (?, ?, ?)",
        [
            ("old-1", "tenant-a", None),
            ("old-2", "tenant-a", None),
            ("old-1", "tenant-b", None),
            ("child-a", "tenant-a", "old-1"),
            ("child-b", "tenant-b", "old-1"),
        ],
    )

    store = AsyncMock(return_value="new-fact")
    archaeologist = _make_archaeologist(l3_conn=l3_conn, l2_conn=l2_conn, store=store)

    await archaeologist._apply_db_updates(
        "proj",
        "tenant-a",
        "condensed",
        ["old-1", "old-2"],
        "root",
        l3_conn,
        l2_conn,
    )

    store.assert_awaited_once_with(
        project="proj",
        content="condensed",
        tenant_id="tenant-a",
        fact_type="knowledge",
        confidence="C5",
        source="cortex_archaeologist",
        meta={"archaeology_merged_from": ["old-1", "old-2"]},
    )

    tenant_a_rows = l3_conn.execute(
        "SELECT id, is_tombstoned, parent_decision_id FROM facts WHERE tenant_id = ? ORDER BY id",
        ("tenant-a",),
    ).fetchall()
    tenant_b_rows = l3_conn.execute(
        "SELECT id, is_tombstoned, parent_decision_id FROM facts WHERE tenant_id = ? ORDER BY id",
        ("tenant-b",),
    ).fetchall()
    tenant_b_meta = l2_conn.execute(
        "SELECT id, parent_decision_id FROM facts_meta WHERE tenant_id = ? ORDER BY id",
        ("tenant-b",),
    ).fetchall()

    assert [(row["id"], row["is_tombstoned"]) for row in tenant_a_rows[:2]] == [
        ("child-a", 0),
        ("old-1", 1),
    ]
    assert tenant_a_rows[2]["id"] == "old-2"
    assert tenant_a_rows[2]["is_tombstoned"] == 1
    assert tenant_a_rows[0]["parent_decision_id"] == "new-fact"

    assert [(row["id"], row["is_tombstoned"], row["parent_decision_id"]) for row in tenant_b_rows] == [
        ("child-b", 0, "old-1"),
        ("old-1", 0, None),
    ]
    assert [(row["id"], row["parent_decision_id"]) for row in tenant_b_meta] == [
        ("child-b", "old-1"),
        ("old-1", None),
    ]
