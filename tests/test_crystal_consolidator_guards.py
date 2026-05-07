from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from cortex.extensions.swarm.crystal_consolidator import (
    ConsolidationResult,
    _execute_cold_purge,
    _execute_semantic_merge,
)
from cortex.extensions.swarm.crystal_thermometer import CrystalVitals


def _vital(fact_id: str, recommendation: str) -> CrystalVitals:
    return CrystalVitals(
        fact_id=fact_id,
        content_preview="preview",
        temperature=0.001,
        resonance=0.01,
        quadrant="DEAD_WEIGHT",
        recommendation=recommendation,  # type: ignore[arg-type]
        age_days=30,
        recall_count=0,
        is_diamond=False,
        project_id="project-a",
    )


@pytest.mark.asyncio
async def test_cold_purge_blocks_physical_l2_delete_and_scopes_tenant():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE facts_meta (
                id TEXT,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                content TEXT,
                metadata TEXT
            )
            """
        )
        conn.execute("CREATE TABLE vec_facts (rowid INTEGER, embedding BLOB)")
        conn.executemany(
            "INSERT INTO facts_meta (id, tenant_id, project_id, content, metadata) VALUES (?, ?, ?, ?, '{}')",
            [
                ("shared", "tenant-a", "project-a", "tenant a crystal"),
                ("shared", "tenant-b", "project-a", "tenant b crystal"),
            ],
        )
        conn.executemany(
            "INSERT INTO vec_facts (rowid, embedding) VALUES (?, ?)",
            [
                (1, np.array([1.0, 0.0], dtype=np.float32).tobytes()),
                (2, np.array([1.0, 0.0], dtype=np.float32).tobytes()),
            ],
        )

        result = ConsolidationResult(total_scanned=1)
        await _execute_cold_purge(conn, [_vital("shared", "PURGE")], result, False, "tenant-a")

        rows = conn.execute(
            "SELECT tenant_id, metadata FROM facts_meta ORDER BY tenant_id"
        ).fetchall()
        vector_count = conn.execute("SELECT COUNT(*) FROM vec_facts").fetchone()[0]
    finally:
        conn.close()

    assert result.blocked == 1
    assert result.purged == 0
    assert rows[0][0] == "tenant-a"
    assert "nightshift_purge_blocked" in rows[0][1]
    assert rows[1] == ("tenant-b", "{}")
    assert vector_count == 2


@pytest.mark.asyncio
async def test_semantic_merge_blocks_direct_synthesis_write_and_delete():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE facts_meta (
                id TEXT,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                content TEXT,
                metadata TEXT
            )
            """
        )
        conn.execute("CREATE TABLE vec_facts (rowid INTEGER, embedding BLOB)")
        conn.executemany(
            "INSERT INTO facts_meta (id, tenant_id, project_id, content, metadata) VALUES (?, ?, ?, ?, '{}')",
            [
                ("a", "tenant-a", "project-a", "primary content"),
                ("b", "tenant-a", "project-a", "secondary content"),
            ],
        )
        emb = np.array([1.0, 0.0], dtype=np.float32).tobytes()
        conn.executemany(
            "INSERT INTO vec_facts (rowid, embedding) VALUES (?, ?)",
            [(1, emb), (2, emb)],
        )

        result = ConsolidationResult(total_scanned=2)
        await _execute_semantic_merge(
            conn,
            [_vital("a", "MERGE"), _vital("b", "MERGE")],
            result,
            False,
            "tenant-a",
        )

        rows = conn.execute("SELECT id, content, metadata FROM facts_meta ORDER BY id").fetchall()
        vector_count = conn.execute("SELECT COUNT(*) FROM vec_facts").fetchone()[0]
    finally:
        conn.close()

    assert result.blocked == 1
    assert result.merged == 0
    assert rows[0][0:2] == ("a", "primary content")
    assert "nightshift_merge_blocked" in rows[0][2]
    assert rows[1] == ("b", "secondary content", "{}")
    assert vector_count == 2
