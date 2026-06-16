# [C5-REAL] Exergy-Maximized

import random
import sqlite3
from typing import Any


def calculate_recall_precision(engine, limit: int = 20, top_k: int = 5) -> dict[str, Any]:
    """Calculates Semantic Recall@K Precision on existing memory facts using synchronous engine."""

    # We access the raw db connection strictly for reading sample rows autonomously
    db_path = getattr(engine, "db_path", None)
    if not db_path:
        # Fallback to defaults
        from cortex.core.paths import CORTEX_DB

        db_path = CORTEX_DB

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, content FROM facts_meta ORDER BY RANDOM() LIMIT ?", (limit,))
            facts = cur.fetchall()
        except sqlite3.OperationalError as e:
            if "no such table: facts_meta" in str(e):
                # If the table doesn't exist, return 0 recall as there are no facts to evaluate
                return {"total": 0, "hits": 0, "recall_at_k": 0.0, "top_k": top_k}
            raise

    hits = 0
    total = len(facts)

    if total == 0:
        return {"recall_at_k": 0.0, "total": 0, "hits": 0, "top_k": top_k}

    for fact_id, content in facts:
        if not content:
            continue

        words = content.split()
        if len(words) > 5:
            start = random.randint(0, len(words) - 5)
            query = " ".join(words[start : start + 5])
        else:
            query = content

        # Call synchronous semantic search
        results = engine.search(content=query, limit=top_k)

        # Check hit condition
        found_ids = [str(r.id) for r in results]

        if str(fact_id) in found_ids:
            hits += 1

    recall = (hits / total) if total > 0 else 0.0
    return {"recall_at_k": round(recall, 4), "total": total, "hits": hits, "top_k": top_k}


def evaluate_belief_score(
    relevance: float,
    confidence: float,
    recency: float,
    token_cost: int,
    risk_contam: float,
    w_r: float = 0.5,
    w_c: float = 0.3,
    w_t: float = 0.2
) -> float:
    """
    Belief Plane (Memory Scheduler) Equation.
    Determines if a belief should be injected into context or rejected.

    Score(m) = ((Rel * w_r) + (Conf * w_c) + (Rec * w_t)) / (Cost_tokens + Risk_contam)

    If Risk_contam approaches infinity (cascading structural contradictions),
    the score asymptotes to 0, rejecting the memory payload.
    """
    if risk_contam >= 1e6:
        # Hard fault / Absolute contradiction
        return 0.0

    numerator = (relevance * w_r) + (confidence * w_c) + (recency * w_t)
    
    # Avoid division by zero
    denominator = max(1.0, float(token_cost)) + risk_contam

    score = numerator / denominator
    return score
