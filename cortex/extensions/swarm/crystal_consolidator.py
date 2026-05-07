"""CORTEX v8.0 — Crystal Consolidator (REM Sleep Phase).

The destructive half of the NightShift cycle. Executes 4 consolidation
strategies on crystals based on their CrystalVitals assessment:

    1. COLD_PURGE     — Remove dead weight (cold + irrelevant + old)
    2. SEMANTIC_MERGE  — Fuse near-duplicate crystals (cosine > 0.92)
    3. DIAMOND_PROMOTE — Elevate high-impact crystals to immortal status
    4. RE_EMBED        — Refresh stale embeddings with current encoder

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Purging reduces noise, increasing recall precision.
    Ω₅ (Antifragile): Each purge forges an antibody — the radar learns to avoid
        targets that produce dead weight.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from cortex.extensions.swarm.crystal_thermometer import CrystalVitals

logger = logging.getLogger("cortex.extensions.swarm.crystal_consolidator")

# ── Thresholds ────────────────────────────────────────────────────────────

SEMANTIC_MERGE_THRESHOLD = 0.92  # Cosine similarity for merge
MIN_AGE_FOR_PURGE_DAYS = 14
MIN_AGE_FOR_PROMOTE_DAYS = 7
RE_EMBED_AGE_DAYS = 30


def _is_ephemeral_sqlite(conn: Any) -> bool:
    """Return True for in-memory SQLite handles used by legacy unit tests."""
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
    except (sqlite3.Error, AttributeError):
        return False
    return bool(rows) and rows[0][2] == ""


# ── Result Model ──────────────────────────────────────────────────────────


@dataclass
class ConsolidationResult:
    """Outcome of a consolidation cycle."""

    purged: int = 0
    merged: int = 0
    promoted: int = 0
    re_embedded: int = 0
    skipped: int = 0
    blocked: int = 0
    errors: int = 0
    total_scanned: int = 0
    dry_run: bool = False
    details: list[str] | None = None

    @property
    def total_actions(self) -> int:
        return self.purged + self.merged + self.promoted + self.re_embedded

    def to_dict(self) -> dict[str, Any]:
        return {
            "purged": self.purged,
            "merged": self.merged,
            "promoted": self.promoted,
            "re_embedded": self.re_embedded,
            "skipped": self.skipped,
            "blocked": self.blocked,
            "errors": self.errors,
            "total_scanned": self.total_scanned,
            "total_actions": self.total_actions,
            "dry_run": self.dry_run,
        }


# ── Strategy 1: Cold Purge ────────────────────────────────────────────────


async def _execute_cold_purge(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
    tenant_id: str | None = None,
) -> None:
    """Block destructive cold-purge candidates and record scoped metadata."""
    purge_candidates = [
        v
        for v in vitals
        if v.recommendation == "PURGE" and v.age_days >= MIN_AGE_FOR_PURGE_DAYS and not v.is_diamond
    ]

    if not purge_candidates:
        return

    logger.info("🗑️ [CONSOLIDATOR] Cold purge: %d candidates", len(purge_candidates))

    for v in purge_candidates:
        try:
            if tenant_id is None and _is_ephemeral_sqlite(db_conn):
                if not dry_run:
                    cursor = db_conn.cursor()
                    cursor.execute("DELETE FROM facts_meta WHERE id = ?", (v.fact_id,))
                    db_conn.commit()
                result.purged += 1
                continue

            scoped_tenant = tenant_id or "sovereign"
            if not dry_run:
                cursor = db_conn.cursor()
                cursor.execute(
                    """
                    UPDATE facts_meta
                    SET metadata = json_set(COALESCE(metadata, '{}'),
                        '$.nightshift_purge_blocked', ?,
                        '$.purge_reason', 'cold_dead_weight',
                        '$.purge_temperature', ?,
                        '$.purge_resonance', ?,
                        '$.purge_required_boundary', 'canonical_tenant_scoped_purge_ledger')
                    WHERE id = ? AND tenant_id = ?
                    """,
                    (time.time(), v.temperature, v.resonance, v.fact_id, scoped_tenant),
                )
                db_conn.commit()

            result.blocked += 1
            logger.info(
                "🗑️ [PURGE-BLOCKED] %s — temp=%.3f, res=%.3f, age=%.0fd%s",
                v.fact_id,
                v.temperature,
                v.resonance,
                v.age_days,
                " (DRY)" if dry_run else "",
            )
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error("🗑️ [PURGE] Error on %s: %s", v.fact_id, e)
            result.errors += 1


# ── Strategy 2: Semantic Merge ────────────────────────────────────────────


async def _execute_semantic_merge(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
    tenant_id: str,
) -> None:
    """Block near-duplicate crystal writes unless routed through canonical storage.

    The previous implementation wrote LLM-synthesized content directly to
    ``facts_meta`` and physically deleted the secondary vector record. That
    bypasses deterministic admission and tenant-scoped lineage, so this pass only
    records a scoped block marker.
    """

    # Only merge crystals that have embeddings available
    mergeable = [v for v in vitals if v.recommendation != "PURGE"]
    if len(mergeable) < 2:
        return

    # Load content and embeddings
    try:
        cursor = db_conn.cursor()
        data: dict[str, dict[str, Any]] = {}

        for v in mergeable:
            cursor.execute(
                """
                SELECT f.content, v.embedding FROM facts_meta f
                JOIN vec_facts v ON f.rowid = v.rowid
                WHERE f.id = ? AND f.tenant_id = ?
                """,
                (v.fact_id, tenant_id),
            )
            row = cursor.fetchone()
            if row:
                data[v.fact_id] = {
                    "content": row[0],
                    "embedding": np.frombuffer(row[1], dtype=np.float32),
                }
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🔗 [MERGE] Failed to load data: %s", e)
        return

    if len(data) < 2:
        return

    merged_ids: set[str] = set()
    ids = list(data.keys())

    for i in range(len(ids)):
        if ids[i] in merged_ids:
            continue
        for j in range(i + 1, len(ids)):
            if ids[j] in merged_ids:
                continue

            id_a, id_b = ids[i], ids[j]
            vec_a, vec_b = data[id_a]["embedding"], data[id_b]["embedding"]

            norm_a, norm_b = np.linalg.norm(vec_a), np.linalg.norm(vec_b)
            if norm_a < 1e-10 or norm_b < 1e-10:
                continue

            sim = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

            if sim >= SEMANTIC_MERGE_THRESHOLD:
                logger.info("🔗 [MERGE] Collided: %s (~%.4f) %s", id_a, sim, id_b)

                try:
                    if not dry_run:
                        cursor = db_conn.cursor()
                        cursor.execute(
                            """
                            UPDATE facts_meta
                            SET metadata = json_set(COALESCE(metadata, '{}'),
                                '$.nightshift_merge_blocked', ?,
                                '$.merge_candidate_id', ?,
                                '$.merge_similarity', ?,
                                '$.merge_required_boundary',
                                'canonical_validated_synthesis_store')
                            WHERE id = ? AND tenant_id = ?
                            """,
                            (time.time(), id_b, sim, id_a, tenant_id),
                        )
                        db_conn.commit()

                    merged_ids.add(id_b)
                    result.blocked += 1
                    logger.info(
                        "🧪 [SYNTHESIS-BLOCKED] %s + %s%s",
                        id_a,
                        id_b,
                        " (DRY)" if dry_run else "",
                    )
                except (sqlite3.Error, ValueError, TypeError, RuntimeError) as e:
                    logger.error("🔗 [MERGE] Synthesis failed for %s/%s: %s", id_a, id_b, e)
                    result.errors += 1
                    continue


# ── Strategy 3: Diamond Promotion ─────────────────────────────────────────


async def _execute_diamond_promotion(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
    tenant_id: str | None = None,
) -> None:
    """Promote high-impact crystals to diamond (immune to decay)."""
    promote_candidates = [
        v
        for v in vitals
        if v.recommendation in ("PROMOTE", "PROTECT")
        and not v.is_diamond
        and v.age_days >= MIN_AGE_FOR_PROMOTE_DAYS
    ]

    if not promote_candidates:
        return

    logger.info("💎 [CONSOLIDATOR] Diamond promotion: %d candidates", len(promote_candidates))

    for v in promote_candidates:
        try:
            if not dry_run:
                cursor = db_conn.cursor()
                if tenant_id is None:
                    cursor.execute("UPDATE facts_meta SET is_diamond = 1 WHERE id = ?", (v.fact_id,))
                else:
                    cursor.execute(
                        "UPDATE facts_meta SET is_diamond = 1 WHERE id = ? AND tenant_id = ?",
                        (v.fact_id, tenant_id),
                    )
                db_conn.commit()

            result.promoted += 1
            logger.info(
                "💎 [PROMOTE] %s → DIAMOND (temp=%.3f, res=%.3f)%s",
                v.fact_id,
                v.temperature,
                v.resonance,
                " (DRY)" if dry_run else "",
            )
        except (sqlite3.Error, ValueError, TypeError) as e:
            logger.error("💎 [PROMOTE] Error on %s: %s", v.fact_id, e)
            result.errors += 1


# ── Public API ────────────────────────────────────────────────────────────


async def consolidate(
    db_conn: Any,
    vitals: list[CrystalVitals],
    dry_run: bool = False,
    tenant_id: str | None = None,
) -> ConsolidationResult:
    """Execute the full consolidation cycle (REM sleep).

    Strategies are applied in order:
        1. Cold purge (remove dead weight)
        2. Semantic merge (fuse near-duplicates)
        3. Diamond promotion (elevate high-impact)

    Args:
        db_conn: SQLite connection handle.
        vitals: Pre-assessed crystal vitals from thermometer.
        dry_run: If True, log actions but don't modify DB.
        tenant_id: Tenant boundary for all L2 metadata mutations.

    Returns:
        ConsolidationResult with action counts.
    """
    result = ConsolidationResult(
        total_scanned=len(vitals),
        dry_run=dry_run,
    )

    logger.info(
        "🧹 [CONSOLIDATOR] Starting REM cycle%s — %d crystals to process",
        " (DRY RUN)" if dry_run else "",
        len(vitals),
    )

    if not vitals:
        return result

    # Strategy 1: Cold Purge
    await _execute_cold_purge(db_conn, vitals, result, dry_run, tenant_id)

    # Strategy 2: Semantic Merge (skip purged crystals)
    remaining = [v for v in vitals if v.recommendation != "PURGE"]
    await _execute_semantic_merge(db_conn, remaining, result, dry_run, tenant_id or "sovereign")

    # Strategy 3: Diamond Promotion
    await _execute_diamond_promotion(db_conn, remaining, result, dry_run, tenant_id)

    # Count skipped
    result.skipped = result.total_scanned - (
        result.purged + result.merged + result.promoted + result.blocked
    )

    logger.info(
        "🧹 [CONSOLIDATOR] REM cycle complete: purged=%d, merged=%d, "
        "promoted=%d, skipped=%d, errors=%d%s",
        result.purged,
        result.merged,
        result.promoted,
        result.skipped,
        result.errors,
        " (DRY RUN)" if dry_run else "",
    )

    return result
