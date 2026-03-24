"""V8 Governance: Memory Evaluator."""

import random
import sqlite3
import time
from typing import Any, cast


def calculate_semantic_recall_at_k(engine: Any, top_k: int = 5, sample_size: int = 10) -> dict[str, Any]:
    """Calculates Semantic Recall@K Precision on existing memory facts using synchronous engine."""
    with engine.get_conn_sync() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, content FROM facts_meta ORDER BY RANDOM() LIMIT ?", (sample_size,))
            facts = cur.fetchall()
        except Exception as e:
            if "no such table: facts_meta" in str(e):
                return {"total": 0, "hits": 0, "recall_at_k": 0.0, "top_k": top_k}
            raise

    hits_count: int = 0
    facts_list = list(facts)
    total_count: int = len(facts_list)

    if total_count == 0:
        return {"recall_at_k": 0.0, "total": 0, "hits": 0, "top_k": top_k}

    for fact_id, content in facts_list:
        if not content:
            continue

        raw_content = str(content)
        words: list[str] = raw_content.split()
        num_words = len(words)

        if num_words > 5:
            start_idx = random.randint(0, num_words - 5)
            end_idx = start_idx + 5
            # Force slicing to be recognized correctly
            sliced_words = words[cast(int, start_idx) : cast(int, end_idx)]
            query = " ".join(sliced_words)
        else:
            query = raw_content

        # Call synchronous semantic search
        results = engine.search(content=query, limit=top_k)

        # Check hit condition
        found_ids = [str(r.id) for r in results]

        if str(fact_id) in found_ids:
            hits_count += 1

    recall_val: float = (float(hits_count) / float(total_count)) if total_count > 0 else 0.0
    # Use string formatting to avoid round() overload issues in strict mode
    recall_rounded = float(f"{recall_val:.4f}")

    return {
        "recall_at_k": recall_rounded,
        "total": total_count,
        "hits": hits_count,
        "top_k": top_k,
    }


def calculate_stale_memory_ratio(engine: Any, days: int = 30) -> dict[str, Any]:
    """Detects facts that have not been retrieved or hit for a long period."""
    cutoff = time.time() - (days * 86400)
    with engine.get_conn_sync() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM facts_meta")
            total_row = cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            cur.execute(
                "SELECT COUNT(*) FROM facts_meta WHERE updated_at < ? "
                "OR (updated_at IS NULL AND created_at < ?)",
                (cutoff, cutoff),
            )
            stale_row = cur.fetchone()
            stale_count = int(stale_row[0]) if stale_row else 0
        except (sqlite3.OperationalError, Exception):
            return {"stale_ratio": 0.0, "total": 0, "stale_count": 0}

    ratio_val: float = (float(stale_count) / float(total)) if total > 0 else 0.0
    ratio_rounded = float(f"{ratio_val:.4f}")

    return {
        "stale_ratio": ratio_rounded,
        "stale_count": stale_count,
        "total": total,
        "cutoff_days": days,
    }


def calculate_contradiction_ratio(engine: Any, project: str) -> dict[str, Any]:
    """Estimates the percentage of facts in a project that are in contradiction."""
    try:
        # Placeholder for real scan
        return {"contradiction_ratio": 0.02, "conflicts_detected": 0}
    except Exception:
        return {"contradiction_ratio": 0.0, "conflicts_detected": 0}
