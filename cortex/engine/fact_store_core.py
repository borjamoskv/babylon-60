"""
Fact Store Core - Low-level storage operations (SQL, FTS, Graph, Causality).
Ω₁: Immutable audit trail and causal linking.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Optional

import aiosqlite

from cortex.memory.temporal import TimestampInput, normalize_timestamp, now_iso
from cortex.utils.canonical import compute_fact_hash

logger = logging.getLogger("cortex")
_TABLE_COLUMNS_CACHE: dict[tuple[int, str], set[str]] = {}
_TABLE_EXISTS_CACHE: dict[tuple[int, str], bool] = {}


async def _get_table_columns(conn: aiosqlite.Connection, table_name: str) -> set[str]:
    """Return the set of column names for a SQLite table."""
    cache_key = (id(conn), table_name)
    cached = _TABLE_COLUMNS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    async with conn.execute(f"PRAGMA table_info({table_name})") as cursor:
        rows = await cursor.fetchall()
    columns = {str(row[1]) for row in rows}
    _TABLE_COLUMNS_CACHE[cache_key] = columns
    return columns


async def _table_exists(conn: aiosqlite.Connection, table_name: str) -> bool:
    """Return True when the table exists in the current database."""
    cache_key = (id(conn), table_name)
    cached = _TABLE_EXISTS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    async with conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ) as cursor:
        exists = await cursor.fetchone() is not None

    _TABLE_EXISTS_CACHE[cache_key] = exists
    return exists


async def _prepare_fact_content(
    content: str, tenant_id: str
) -> tuple[str, str, Optional[str], Optional[str]]:
    """Encrypted content and cryptographic signatures."""
    from cortex.crypto import get_default_encrypter
    from cortex.extensions.security.signatures import get_default_signer

    f_hash = compute_fact_hash(content)
    enc = get_default_encrypter()
    encrypted_content = enc.encrypt_str(content, tenant_id=tenant_id)
    if encrypted_content is None:
        raise ValueError("Content encryption returned no ciphertext")

    sig_b64, pub_b64 = None, None
    try:
        signer = get_default_signer()
        if signer and signer.can_sign:
            sig_b64 = signer.sign(content, f_hash)
            pub_b64 = signer.public_key_b64
    except (ImportError, ValueError, OSError) as e:
        logger.debug("Fact signing skipped: %s", e)

    return f_hash, encrypted_content, sig_b64, pub_b64


async def _resolve_causal_parent(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    fact_type: str,
    parent_decision_id: Optional[int],
) -> Optional[int]:
    """Validate or auto-resolve the parent decision link."""
    if parent_decision_id is not None:
        async with conn.execute(
            "SELECT id FROM facts WHERE id = ? AND tenant_id = ?",
            (parent_decision_id, tenant_id),
        ) as cursor:
            if await cursor.fetchone() is None:
                logger.warning("parent_decision_id=%d non-existent — cleared", parent_decision_id)
                return None
        return parent_decision_id

    if fact_type in ("decision", "error"):
        async with conn.execute(
            "SELECT id FROM facts WHERE project = ? AND tenant_id = ? "
            "AND fact_type = 'decision' AND is_tombstoned = 0 "
            "ORDER BY id DESC LIMIT 1",
            (project, tenant_id),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            logger.debug("Auto-resolved parent=%d for %s", row[0], fact_type)
            return row[0]
    return None


async def insert_fact_record(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    content: str,
    fact_type: str,
    tags: Optional[list[str]],
    confidence: str,
    ts: TimestampInput,
    source: Optional[str],
    meta: Optional[dict[str, Any]],
    tx_id: Optional[int],
    parent_decision_id: Optional[int] = None,
) -> int:
    """Perform the actual SQL insert into the facts table."""
    ts = normalize_timestamp(ts) or now_iso()
    tags_json = json.dumps(tags or [])
    meta = meta or {}

    f_hash, encrypted_content, sig_b64, pub_b64 = await _prepare_fact_content(content, tenant_id)

    parent_decision_id = await _resolve_causal_parent(
        conn, tenant_id, project, fact_type, parent_decision_id
    )

    # 3. SQL Persistence
    payload = await _build_fact_payload(
        conn,
        tenant_id,
        project,
        encrypted_content,
        fact_type,
        meta,
        f_hash,
        source,
        confidence,
        parent_decision_id,
        tx_id,
        tags_json,
        ts,
    )

    columns_sql = ", ".join(column for column, _ in payload)
    placeholders_sql = ", ".join("?" for _ in payload)
    values = [value for _, value in payload]

    async with conn.execute(
        f"INSERT INTO facts ({columns_sql}) VALUES ({placeholders_sql})",
        values,
    ) as cursor:
        fact_id = cursor.lastrowid
    assert fact_id is not None

    await _post_insert_actions(
        conn,
        fact_id,
        content,
        tenant_id,
        project,
        tags,
        tags_json,
        fact_type,
        ts,
        meta,
        parent_decision_id,
    )

    return fact_id


async def _build_fact_payload(
    conn: aiosqlite.Connection,
    tenant_id: str,
    project: str,
    encrypted_content: str,
    fact_type: str,
    meta: dict[str, Any],
    f_hash: str,
    source: Optional[str],
    confidence: str,
    parent_decision_id: Optional[int],
    tx_id: Optional[int],
    tags_json: str,
    ts: str,
) -> list[tuple[str, Any]]:
    """Construct the SQL payload with layout-aware column detection."""
    from cortex.crypto import get_default_encrypter
    from cortex.engine.metadata_engine import MetadataEngine
    from cortex.engine.models import Fact

    temp_fact = Fact(
        id=0,
        tenant_id=tenant_id,
        project=project,
        content="",
        fact_type=fact_type,
        tags=[],
        parent_id=parent_decision_id,
        relation_type=meta.get("relation_type"),
    )
    m2 = MetadataEngine.classify_deterministic(temp_fact)

    rank_map = {"C5": 5, "C4": 4, "C3": 3, "C2": 2, "C1": 1, "stated": 5, "verified": 5}
    c_rank = rank_map.get(confidence, 3)

    facts_columns = await _get_table_columns(conn, "facts")
    payload: list[tuple[str, Any]] = []

    def add(col: str, val: Any) -> None:
        if col in facts_columns:
            payload.append((col, val))

    add("tenant_id", tenant_id)
    add("project", project)
    add("content", encrypted_content)
    add("fact_type", fact_type)

    enc = get_default_encrypter()
    meta_json = enc.encrypt_json(meta, tenant_id=tenant_id) if meta else json.dumps(meta)
    if "metadata" in facts_columns:
        add("metadata", meta_json)
    elif "meta" in facts_columns:
        add("meta", meta_json)

    add("hash", f_hash)
    add("source", source)
    add("confidence", confidence)
    add("confidence_rank", c_rank)
    add("consensus_score", float(meta.get("consensus_score", 1.0)))
    if "parent_id" in facts_columns:
        add("parent_id", parent_decision_id)
    elif "parent_decision_id" in facts_columns:
        add("parent_decision_id", parent_decision_id)

    add("relation_type", m2["relation_type"])
    add("quadrant", m2["quadrant"])
    add("storage_tier", m2["storage_tier"])
    add("exergy_score", m2["exergy_score"])
    add("category", m2["category"])
    add("yield_score", m2["yield_score"])
    add("semantic_status", "pending")
    add("tags", tags_json)
    add("tx_id", tx_id)
    add("created_at", ts)
    add("updated_at", ts)
    add("valid_from", ts)
    return payload


async def _record_causality(
    conn: aiosqlite.Connection,
    fact_id: int,
    project: str,
    tenant_id: str,
    meta: dict[str, Any],
    parent_decision_id: Optional[int],
) -> None:
    """Record causal linkage for the fact."""
    if not await _table_exists(conn, "causal_edges"):
        return

    try:
        from cortex.engine.causality import EDGE_DERIVED_FROM, EDGE_TRIGGERED_BY, EDGE_UPDATED_FROM

        p_sig = meta.get("causal_parent")
        p_fact = meta.get("previous_fact_id")

        if p_sig or p_fact:
            e_type = EDGE_UPDATED_FROM if p_fact else EDGE_TRIGGERED_BY
            await conn.execute(
                "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, p_fact, p_sig, e_type, project, tenant_id),
            )
        elif parent_decision_id:
            await conn.execute(
                "INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id) "
                "VALUES (?, ?, NULL, ?, ?, ?)",
                (fact_id, parent_decision_id, EDGE_DERIVED_FROM, project, tenant_id),
            )
    except sqlite3.Error as e:
        logger.debug(
            "Skipping causal edge write for fact_id=%s tenant_id=%s: %s",
            fact_id,
            tenant_id,
            e,
        )


async def _post_insert_actions(
    conn: aiosqlite.Connection,
    fact_id: int,
    content: str,
    tenant_id: str,
    project: str,
    tags: Optional[list[str]],
    tags_json: str,
    fact_type: str,
    ts: str,
    meta: dict[str, Any],
    parent_decision_id: Optional[int],
) -> None:
    """Side effects required on the main write path."""
    meta = meta or {}

    if await _table_exists(conn, "enrichment_jobs"):
        try:
            await conn.execute(
                "INSERT INTO enrichment_jobs (fact_id, job_type, status, priority) VALUES (?, 'embedding', 'pending', ?)",
                (fact_id, 1 if fact_type == "decision" else 0),
            )
        except sqlite3.Error as e:
            logger.debug("Skipping enrichment job write for fact_id=%s: %s", fact_id, e)

    if tags and await _table_exists(conn, "fact_tags"):
        fact_tags_columns = await _get_table_columns(conn, "fact_tags")
        if {"fact_id", "tag"}.issubset(fact_tags_columns):
            if "tenant_id" in fact_tags_columns:
                await conn.executemany(
                    "INSERT OR IGNORE INTO fact_tags (fact_id, tag, tenant_id) VALUES (?, ?, ?)",
                    [(fact_id, t, tenant_id) for t in tags],
                )
            else:
                await conn.executemany(
                    "INSERT OR IGNORE INTO fact_tags (fact_id, tag) VALUES (?, ?)",
                    [(fact_id, t) for t in tags],
                )

    if await _table_exists(conn, "facts_fts"):
        try:
            fts_columns = await _get_table_columns(conn, "facts_fts")
            payload: list[tuple[str, Any]] = [
                ("rowid", fact_id),
                ("content", content),
                ("project", project),
            ]
            if "tags" in fts_columns:
                payload.append(("tags", tags_json))
            if "fact_type" in fts_columns:
                payload.append(("fact_type", fact_type))
            if "tenant_id" in fts_columns:
                payload.append(("tenant_id", tenant_id))

            if payload:
                columns_sql = ", ".join(col for col, _ in payload)
                placeholders_sql = ", ".join("?" for _ in payload)
                values = [value for _, value in payload]
                await conn.execute(
                    f"INSERT INTO facts_fts ({columns_sql}) VALUES ({placeholders_sql})",
                    values,
                )
        except sqlite3.Error as e:
            logger.debug("Skipping FTS write for fact_id=%s: %s", fact_id, e)

    await _record_causality(conn, fact_id, project, tenant_id, meta, parent_decision_id)


async def resolve_causality_async(
    conn: aiosqlite.Connection,
    project: str,
    meta: Optional[dict[str, Any]],
    tenant_id: str = "default",
) -> dict[str, Any]:
    """Resolve causal linking for a fact asynchronously.

    Ω₁: Every decision must point to its progenitor.
    """
    from cortex.engine.causality import AsyncCausalOracle, link_causality

    if not (meta and meta.get("causal_parent")):
        parent_sig = await AsyncCausalOracle.find_parent_signal(
            conn,
            tenant_id=tenant_id,
            project=project,
        )
        return link_causality(meta, parent_sig)
    return meta or {}


def resolve_causality(
    db_path: Optional[str], project: str, meta: Optional[dict[str, Any]], tenant_id: str = "default"
) -> dict[str, Any]:
    """Resolve causal linking for a fact (sync)."""
    from cortex.engine.causality import CausalOracle, link_causality

    if db_path and not (meta and meta.get("causal_parent")):
        parent_sig = CausalOracle.find_parent_signal(
            db_path,
            tenant_id=tenant_id,
            project=project,
        )
        return link_causality(meta, parent_sig)
    return meta or {}
