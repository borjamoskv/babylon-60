"""CORTEX v9 — Causality Reranker (Structural Gap Reduction).

Enforces Ω₂: Similarity is insufficient. Search must seek causal gaps.
This module ranks retrieved context by its mechanical utility (Exergy)
in resolving the current objective's structural dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger("cortex.memory.causality")


class CausalEdgeProvider(Protocol):
    """Protocol for components that provide causal graph edges (e.g., STDP, Ledger)."""
    def get_edge_weight(self, source_id: str, target_id: str) -> float: ...


class CausalityReranker:
    """Reranks memory retrieval results based on causal connectivity and gap reduction.

    Attributes:
        causal_gap_reduction_required: If True, results with zero causal link to the
            objective are heavily penalized (Ω₂ enforcement).
    """

    def __init__(
        self,
        edge_provider: CausalEdgeProvider | None = None,
        causal_gap_reduction_required: bool = True,
    ):
        self._edges = edge_provider
        self._enforce_gap = causal_gap_reduction_required

    def rerank(
        self,
        results: list[dict[str, Any]],
        objective_id: str | None = None,
        context_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Rerank a set of retrieved engrams.

        Args:
            results: List of engram dicts (from RRF).
            objective_id: The ID of the current active goal or task.
            context_ids: IDs already present in the context window to detect redundancy.

        Returns:
            Sorted list of engram dicts with updated 'score'.
        """
        if not results:
            return []

        if not self._edges or not objective_id:
            logger.debug("CausalityReranker: Missing edges or objective_id, skipping rerank")
            return results

        boosted = []
        # Ensure objective_id is a string for the edge provider
        obj_id_str = str(objective_id)

        for item in results:
            engram_id = str(item.get("id", ""))

            # 1. Causal Bridge Score: How well does this fact connect to the GOAL?
            causal_bridge = float(self._edges.get_edge_weight(engram_id, obj_id_str))

            # 2. Novelty/Exergy: If it's already in context_ids, utility is zero
            novelty = 1.0
            if context_ids and engram_id in context_ids:
                novelty = 0.1

            # 3. Mechanical Weighting (Ω₂)
            original_score = float(item.get("score", 0.0))

            # exergy = work useful extraíble
            exergy_score = original_score * (0.5 + 2.0 * causal_bridge) * novelty

            if self._enforce_gap and causal_bridge < 0.01:
                # Penalize disconnected 'thermal noise'
                exergy_score *= 0.1

            # Update item with new scores
            new_item = dict(item)
            new_item["score"] = round(exergy_score, 6)
            new_item["causal_bridge"] = round(causal_bridge, 4)
            boosted.append(new_item)

        # Sort by updated exergy score
        boosted.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        logger.debug(
            "CausalityReranker: Reranked %d items for objective=%s",
            len(boosted),
            obj_id_str
        )
        return boosted
