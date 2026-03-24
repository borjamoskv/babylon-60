# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Vector search implementation."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from cortex.crypto import CortexEncrypter

from cortex.memory.temporal import build_temporal_filter_params
from cortex.search.models import SearchResult
from cortex.storage.qdrant import get_vector_backend

__all__ = ["semantic_search", "semantic_search_sync"]

logger = logging.getLogger("cortex.search.vector")

# ─── SQL fragment constants ────────────────────────────────
_FILTER_PROJECT = " AND f.project = ?"
_FILTER_ACTIVE = " AND f.valid_until IS NULL"


async def semantic_search(
    conn: aiosqlite.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    tenant_id: str = "default",
    project: str | None = None,
    as_of: str | None = None,
    confidence: str | None = None,
) -> list[SearchResult]:
    """Perform semantic vector search using sqlite-vec."""
    vector_backend = get_vector_backend()
    if vector_backend is not None:
        return await _semantic_search_qdrant(
            conn=conn,
            query_embedding=query_embedding,
            top_k=top_k,
            tenant_id=tenant_id,
            project=project,
            as_of=as_of,
            confidence=confidence,
        )

    embedding_json = json.dumps(query_embedding)
    sql, params = _build_semantic_query(
        tenant_id, embedding_json, top_k, project, as_of, confidence
    )

    try:
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
    except (aiosqlite.Error, sqlite3.Error, ValueError) as e:
        logger.error("Semantic search failed: %s", e)
        return []

    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    return [_row_to_result(row, enc, tenant_id) for row in rows[:top_k]]  # type: ignore[reportIndexIssue]


async def _semantic_search_qdrant(
    conn: aiosqlite.Connection,
    query_embedding: list[float],
    top_k: int,
    tenant_id: str,
    project: str | None,
    as_of: str | None,
    confidence: str | None,
) -> list[SearchResult]:
    """Perform semantic search through the configured remote Qdrant backend."""
    vector_backend = get_vector_backend()
    if vector_backend is None:
        return []

    try:
        hits = await vector_backend.search(
            query_embedding=query_embedding,
            top_k=top_k * 3,
            tenant_id=tenant_id,
            project=project,
        )
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Qdrant semantic search failed: %s", e)
        return []

    if not hits:
        return []

    sql, params = _build_qdrant_fact_query(
        fact_ids=[fact_id for fact_id, _score in hits],
        tenant_id=tenant_id,
        project=project,
        as_of=as_of,
        confidence=confidence,
    )

    try:
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
    except (aiosqlite.Error, sqlite3.Error, ValueError) as e:
        logger.error("Qdrant fact hydration failed: %s", e)
        return []

    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()
    row_map = {int(row[0]): row for row in rows}
    results: list[SearchResult] = []

    for fact_id, score in hits:
        row = row_map.get(fact_id)
        if row is None:
            continue
        result = _row_to_result(row, enc, tenant_id, score_override=float(score))
        results.append(result)
        if len(results) >= top_k:
            break

    return results


def _build_semantic_query(
    tenant_id: str,
    embedding_json: str,
    top_k: int,
    project: str | None,
    as_of: str | None,
    confidence: str | None,
) -> tuple[str, list]:
    """Internal helper to build semantic search SQL."""
    sql = """
        SELECT
            f.id, f.content, f.project, f.fact_type, f.confidence,
            f.valid_from, f.valid_until, f.tags, f.source, f.metadata,
            ve.distance, f.created_at, f.updated_at, f.tx_id, f.hash
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        WHERE f.tenant_id = ?
            AND ve.embedding MATCH ?
            AND k = ?
    """
    params = [tenant_id, embedding_json, top_k * 3]

    if project:
        sql += _FILTER_PROJECT
        params.append(project)

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += _FILTER_ACTIVE

    if confidence:
        from cortex.search.utils import get_higher_confidences

        allowed = get_higher_confidences(confidence)
        placeholders = ", ".join("?" for _ in allowed)
        sql += f" AND f.confidence IN ({placeholders})"
        params.extend(allowed)

    sql += " ORDER BY ve.distance ASC"
    return sql, params


def _build_qdrant_fact_query(
    fact_ids: list[int],
    tenant_id: str,
    project: str | None,
    as_of: str | None,
    confidence: str | None,
) -> tuple[str, list[Any]]:
    """Build fact hydration SQL for Qdrant hits."""
    placeholders = ", ".join("?" for _ in fact_ids)
    sql = f"""
        SELECT
            f.id, f.content, f.project, f.fact_type, f.confidence,
            f.valid_from, f.valid_until, f.tags, f.source, f.metadata,
            NULL AS distance, f.created_at, f.updated_at, f.tx_id, f.hash
        FROM facts AS f
        WHERE f.tenant_id = ?
            AND f.id IN ({placeholders})
    """
    params: list[Any] = [tenant_id, *fact_ids]

    if project:
        sql += _FILTER_PROJECT
        params.append(project)

    if as_of:
        clause, t_params = build_temporal_filter_params(as_of, table_alias="f")
        sql += " AND " + clause
        params.extend(t_params)
    else:
        sql += _FILTER_ACTIVE

    if confidence:
        from cortex.search.utils import get_higher_confidences

        allowed = get_higher_confidences(confidence)
        allowed_placeholders = ", ".join("?" for _ in allowed)
        sql += f" AND f.confidence IN ({allowed_placeholders})"
        params.extend(allowed)

    return sql, params


def _row_to_result(
    row: tuple[Any, ...] | aiosqlite.Row,
    enc: CortexEncrypter,
    tenant_id: str,
    score_override: float | None = None,
) -> SearchResult:
    """Helper to parse a search result row with decryption and metadata processing."""
    try:
        tags = json.loads(row[7]) if row[7] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    from cortex.search.utils import _decrypt_row_content, _parse_row_meta

    content = _decrypt_row_content(row[1], tenant_id, enc)
    meta = _parse_row_meta(row[9], tenant_id, enc)

    score = score_override if score_override is not None else 1.0 - (row[10] if row[10] else 0.0)

    return SearchResult(
        fact_id=row[0],
        content=content,  # type: ignore[reportArgumentType]
        project=row[2],
        fact_type=row[3],
        confidence=row[4],
        valid_from=row[5],
        valid_until=row[6],
        tags=tags,
        source=row[8],
        meta=meta,  # type: ignore[reportArgumentType]
        score=score,
        created_at=row[11],
        updated_at=row[12],
        tx_id=row[13],
        hash=row[14],
    )


def semantic_search_sync(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 5,
    tenant_id: str = "default",
    project: str | None = None,
    confidence: str | None = None,
) -> list[SearchResult]:
    """Vector KNN search (sync)."""
    embedding_json = json.dumps(query_embedding)

    sql = """
        SELECT
            f.id, f.content, f.project, f.fact_type, f.confidence,
            f.source, f.tags, ve.distance, f.created_at, f.updated_at, f.tx_id, f.hash
        FROM fact_embeddings AS ve
        JOIN facts AS f ON f.id = ve.fact_id
        WHERE f.tenant_id = ?
            AND ve.embedding MATCH ?
            AND k = ?
            AND f.valid_until IS NULL
    """
    params: list = [tenant_id, embedding_json, top_k * 3]
    if project:
        sql += _FILTER_PROJECT
        params.append(project)
    if confidence:
        from cortex.search.utils import get_higher_confidences

        allowed = get_higher_confidences(confidence)
        placeholders = ", ".join("?" for _ in allowed)
        sql += f" AND f.confidence IN ({placeholders})"
        params.extend(allowed)
    sql += " ORDER BY ve.distance ASC"

    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
    except (sqlite3.Error, ValueError) as e:
        logger.error("Semantic search sync failed: %s", e)
        return []

    from cortex.crypto import get_default_encrypter
    from cortex.search.utils import _decrypt_row_content

    enc = get_default_encrypter()

    results = []
    for row in rows[:top_k]:
        try:
            tags = json.loads(row[6]) if row[6] else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        content = _decrypt_row_content(row[1], tenant_id, enc)

        score = 1.0 - (row[7] if row[7] else 0.0)
        results.append(
            SearchResult(
                fact_id=row[0],
                content=content,  # type: ignore[type-error]
                project=row[2],
                fact_type=row[3],
                confidence=row[4],
                source=row[5],
                tags=tags,
                score=score,
                valid_from="unknown",
                valid_until=None,
                created_at=row[8] or "unknown",
                updated_at=row[9] or "unknown",
                tx_id=row[10],
                hash=row[11],
            )
        )
    return results
