"""Taint Propagation Engine — Axiom Ω₁₃ Enforcement.

When a fact_node is invalidated or loses confidence, propagate impact
to descendants and recalculate effective_confidence. Without this,
derived facts float on cadáveres perfumados — structurally elegant,
epistemically corrupt.

Algorithm: BFS from invalidated node.
- Invalidated node → TAINTED, effective_confidence = C1
- Direct children → minimum SUSPECT
- Children with ≥50% TAINTED parents → TAINTED
- Recalculate effective_confidence at every touched node

Enforcement: derived persistence is blocked if taint_status != CLEAN.
"""

from __future__ import annotations

import logging

from cortex.extensions.causality.models import (
    CONFIDENCE_ORDER,
    REVERSE_CONFIDENCE_ORDER,
    Confidence,
    FactNode,
    TaintStatus,
)

__all__ = [
    "downgrade_confidence",
    "propagate_taint",
    "recompute_effective_confidence",
]

logger = logging.getLogger("cortex.extensions.causality.taint")


try:
    from cortex.cortex_rs import propagate_taint as rs_propagate_taint
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

def downgrade_confidence(base: Confidence, steps: int) -> Confidence:
    """Degrade confidence by N ordinal steps, clamped to C1."""
    value = max(1, CONFIDENCE_ORDER[base] - steps)
    return REVERSE_CONFIDENCE_ORDER[value]

def recompute_effective_confidence(
    node: FactNode,
    graph: dict[str, FactNode],
) -> None:
    """Recalculate effective_confidence based on parent taint states."""
    if node.invalidated or node.taint_status == TaintStatus.TAINTED:
        node.effective_confidence = Confidence.C1
        return

    tainted_parents = sum(
        1
        for pid in node.parents
        if pid in graph and graph[pid].taint_status == TaintStatus.TAINTED
    )
    suspect_parents = sum(
        1
        for pid in node.parents
        if pid in graph and graph[pid].taint_status == TaintStatus.SUSPECT
    )

    if tainted_parents > 0:
        node.effective_confidence = downgrade_confidence(node.confidence, 2)
    elif suspect_parents > 0:
        node.effective_confidence = downgrade_confidence(node.confidence, 1)
    else:
        node.effective_confidence = node.confidence

def propagate_taint(
    start_fact_id: str,
    graph: dict[str, FactNode],
) -> set[str]:
    """Propagate taint from an invalidated fact through the causal DAG."""
    if start_fact_id not in graph:
        raise KeyError(f"Unknown fact_id: {start_fact_id}")

    if _USE_RUST:
        touched, updated_graph = rs_propagate_taint(start_fact_id, graph)
        # Update the original graph dictionary in-place
        graph.update(updated_graph)
        logger.info("Taint propagated (Rust) — %d nodes touched", len(touched))
        return touched

    # Python Fallback
    touched: set[str] = set()
    queue: list[str] = [start_fact_id]
    start = graph[start_fact_id]
    start.invalidated = True
    start.taint_status = TaintStatus.TAINTED
    start.effective_confidence = Confidence.C1

    while queue:
        current_id = queue.pop(0)
        current = graph[current_id]
        touched.add(current_id)

        for child_id in current.children:
            if child_id not in graph:
                continue
            child = graph[child_id]
            if child.taint_status == TaintStatus.CLEAN:
                child.taint_status = TaintStatus.SUSPECT
            parent_count = len(child.parents)
            if parent_count > 0:
                tainted_count = sum(1 for pid in child.parents if pid in graph and graph[pid].taint_status == TaintStatus.TAINTED)
                if tainted_count / parent_count >= 0.5:
                    child.taint_status = TaintStatus.TAINTED
            recompute_effective_confidence(child, graph)
            if child_id not in touched:
                queue.append(child_id)
    return touched

