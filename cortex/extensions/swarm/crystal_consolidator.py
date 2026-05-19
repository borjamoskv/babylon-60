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


# ── Result Model ──────────────────────────────────────────────────────────


@dataclass
class ConsolidationResult:
    """Outcome of a consolidation cycle."""

    purged: int = 0
    merged: int = 0
    promoted: int = 0
    re_embedded: int = 0
    skipped: int = 0
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
) -> None:
    """Remove dead weight crystals (cold + irrelevant + old + not diamond)."""
    purge_candidates = [
        v
        for v in vitals
        if v.recommendation == "PURGE" and v.age_days >= MIN_AGE_FOR_PURGE_DAYS and not v.is_diamond
    ]

    if not purge_candidates:
        return

    logger.info("🗑️ [CONSOLIDATOR] Cold purge: %d candidates", len(purge_candidates))

    try:
        if not dry_run:
            cursor = db_conn.cursor()
            now = time.time()
            chunk_size = 900

            for i in range(0, len(purge_candidates), chunk_size):
                chunk = purge_candidates[i : i + chunk_size]
                ids = [v.fact_id for v in chunk]
                placeholders = ",".join("?" for _ in ids)

                # Soft delete requires individual updates since temp/resonance vary
                for v in chunk:
                    cursor.execute(
                        """
                        UPDATE facts_meta
                        SET metadata = json_set(COALESCE(metadata, '{}'),
                            '$.nightshift_purged', ?,
                            '$.purge_reason', 'cold_dead_weight',
                            '$.purge_temperature', ?,
                            '$.purge_resonance', ?)
                        WHERE id = ?
                        """,
                        (now, v.temperature, v.resonance, v.fact_id),
                    )

                # Actually remove from vector index for recall hygiene (batched)
                cursor.execute(
                    f"DELETE FROM vec_facts WHERE rowid IN "
                    f"(SELECT rowid FROM facts_meta WHERE id IN ({placeholders}))",
                    tuple(ids),
                )
                # Delete from facts_meta (batched)
                cursor.execute(f"DELETE FROM facts_meta WHERE id IN ({placeholders})", tuple(ids))

            db_conn.commit()

        for v in purge_candidates:
            result.purged += 1
            logger.info(
                "🗑️ [PURGE] %s — temp=%.3f, res=%.3f, age=%.0fd%s",
                v.fact_id,
                v.temperature,
                v.resonance,
                v.age_days,
                " (DRY)" if dry_run else "",
            )
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🗑️ [PURGE] Error during batch purge: %s", e)
        result.errors += len(purge_candidates)


# ── Strategy 2: Semantic Merge ────────────────────────────────────────────


async def _execute_semantic_merge(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
) -> None:
    """Merge near-duplicate crystals (cosine > threshold).

    Uses LLM synthesis to fuse content if they are highly similar,
    preserving unique details from both.
    """
    from cortex.extensions.swarm.crystal_synthesis import synthesize_crystals

    # Only merge crystals that have embeddings available
    mergeable = [v for v in vitals if v.recommendation != "PURGE"]
    if len(mergeable) < 2:
        return

    # Load content and embeddings in batches
    try:
        cursor = db_conn.cursor()
        data: dict[str, dict[str, Any]] = {}
        chunk_size = 900

        for i in range(0, len(mergeable), chunk_size):
            chunk = mergeable[i : i + chunk_size]
            ids = [v.fact_id for v in chunk]
            placeholders = ",".join("?" for _ in ids)

            cursor.execute(
                f"""
                SELECT f.id, f.content, v.embedding FROM facts_meta f
                JOIN vec_facts v ON f.rowid = v.rowid
                WHERE f.id IN ({placeholders})
                """,
                tuple(ids),
            )
            rows = cursor.fetchall()
            for row in rows:
                data[row[0]] = {
                    "content": row[1],
                    "embedding": np.frombuffer(row[2], dtype=np.float32),
                }
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("🔗 [MERGE] Failed to load data: %s", e)
        return

    if len(data) < 2:
        return

    ids = list(data.keys())
    embeddings = np.array([data[i]["embedding"] for i in ids])

    # Vectorized similarity calculation
    norms = np.linalg.norm(embeddings, axis=1)
    # Avoid division by zero
    norms[norms < 1e-10] = 1.0

    normalized_embeddings = embeddings / norms[:, np.newaxis]
    similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)

    merged_ids: set[str] = set()
    synthesis_tasks = []

    async def _synthesize_pair(id_a: str, id_b: str, sim: float) -> tuple[str, str, str, str | None]:
        logger.info("🔗 [MERGE] Collided: %s (~%.4f) %s", id_a, sim, id_b)
        try:
            synthesis = await synthesize_crystals(
                primary_content=data[id_a]["content"],
                secondary_content=data[id_b]["content"],
            )
            return id_a, id_b, synthesis.get("fused_content", data[id_a]["content"]), None
        except Exception as e:
            logger.error("🔗 [MERGE] Synthesis failed for %s/%s: %s", id_a, id_b, e)
            return id_a, id_b, "", str(e)

    for i in range(len(ids)):
        if ids[i] in merged_ids:
            continue
        for j in range(i + 1, len(ids)):
            if ids[j] in merged_ids or ids[i] in merged_ids:
                continue

            sim = float(similarity_matrix[i, j])
            if sim >= SEMANTIC_MERGE_THRESHOLD:
                merged_ids.add(ids[i])
                merged_ids.add(ids[j])
                synthesis_tasks.append(_synthesize_pair(ids[i], ids[j], sim))

    if not synthesis_tasks:
        return

    import asyncio
    results = await asyncio.gather(*synthesis_tasks)

    cursor = db_conn.cursor()
    now = time.time()
    for id_a, id_b, new_content, error in results:
        if error:
            result.errors += 1
            continue

        if not dry_run:
            try:
                # Update primary with fused content
                cursor.execute(
                    "UPDATE facts_meta SET content = ?, updated_at = ? WHERE id = ?",
                    (new_content, now, id_a),
                )
                # Delete the secondary
                cursor.execute(
                    "DELETE FROM vec_facts WHERE rowid IN "
                    "(SELECT rowid FROM facts_meta WHERE id = ?)",
                    (id_b,),
                )
                cursor.execute("DELETE FROM facts_meta WHERE id = ?", (id_b,))
            except sqlite3.Error as e:
                logger.error("🔗 [MERGE] DB update failed for %s/%s: %s", id_a, id_b, e)
                result.errors += 1
                continue

        result.merged += 1
        logger.info(
            "🧪 [SYNTHESIS] %s + %s → Unified Crystal%s",
            id_a,
            id_b,
            " (DRY)" if dry_run else "",
        )

    if not dry_run:
        db_conn.commit()


# ── Strategy 3: Diamond Promotion ─────────────────────────────────────────


async def _execute_diamond_promotion(
    db_conn: Any,
    vitals: list[CrystalVitals],
    result: ConsolidationResult,
    dry_run: bool,
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

    try:
        if not dry_run:
            cursor = db_conn.cursor()
            chunk_size = 900

            for i in range(0, len(promote_candidates), chunk_size):
                chunk = promote_candidates[i : i + chunk_size]
                ids = [v.fact_id for v in chunk]
                placeholders = ",".join("?" for _ in ids)

                cursor.execute(
                    f"UPDATE facts_meta SET is_diamond = 1 WHERE id IN ({placeholders})",
                    tuple(ids),
                )

            db_conn.commit()

        for v in promote_candidates:
            result.promoted += 1
            logger.info(
                "💎 [PROMOTE] %s → DIAMOND (temp=%.3f, res=%.3f)%s",
                v.fact_id,
                v.temperature,
                v.resonance,
                " (DRY)" if dry_run else "",
            )
    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("💎 [PROMOTE] Error during batch promotion: %s", e)
        result.errors += len(promote_candidates)


# ── Public API ────────────────────────────────────────────────────────────


async def consolidate(
    db_conn: Any,
    vitals: list[CrystalVitals],
    dry_run: bool = False,
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
    await _execute_cold_purge(db_conn, vitals, result, dry_run)

    # Strategy 2: Semantic Merge (skip purged crystals)
    remaining = [v for v in vitals if v.recommendation != "PURGE"]
    await _execute_semantic_merge(db_conn, remaining, result, dry_run)

    # Strategy 3: Diamond Promotion
    await _execute_diamond_promotion(db_conn, remaining, result, dry_run)

    # Count skipped
    result.skipped = result.total_scanned - (result.purged + result.merged + result.promoted)

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
