"""Deterministic helpers for the continual-learning control plane."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

import numpy as np

__all__ = [
    "agem_project",
    "centroid_distance_projection",
    "compute_cfs",
    "compute_priority",
    "cosine_similarity",
    "ks_2samp",
    "population_stability_index",
    "risk_score",
    "schedule_learning_rate",
    "stable_text_hash",
]


def stable_text_hash(text: str) -> str:
    """Return a stable SHA3-256 digest for sanitized text."""
    return hashlib.sha3_256(text.encode("utf-8")).hexdigest()


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.size == 0 or b.size == 0 or a.shape != b.shape:
        return 0.0

    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0.0 or b_norm == 0.0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def compute_priority(
    confidence: float, novelty: float, cost_of_error: float | None = None
) -> float:
    """Score an interaction for replay priority.

    ``cost_of_error`` increases retention pressure, but is normalized so the
    priority remains bounded and stable across tenants.
    """
    bounded_confidence = min(max(confidence, 0.0), 1.0)
    bounded_novelty = max(novelty, 0.0)
    normalized_cost = 0.0
    if cost_of_error is not None and cost_of_error > 0.0:
        normalized_cost = cost_of_error / (1.0 + cost_of_error)
    return bounded_confidence * bounded_novelty * (1.0 + normalized_cost)


def risk_score(
    confidence: float,
    cost_of_error: float | None = None,
    *,
    policy_violation: bool = False,
    confidence_weight: float = 0.6,
    error_weight: float = 0.4,
    policy_penalty: float = 0.2,
) -> float:
    """Collapse confidence and error-cost into a conservative risk score."""
    bounded_confidence = min(max(confidence, 0.0), 1.0)
    normalized_cost = 0.0
    if cost_of_error is not None and cost_of_error > 0.0:
        normalized_cost = cost_of_error / (1.0 + cost_of_error)

    risk = ((1.0 - bounded_confidence) * confidence_weight) + (normalized_cost * error_weight)
    if policy_violation:
        risk += policy_penalty
    return min(max(risk, 0.0), 1.0)


def schedule_learning_rate(
    base_learning_rate: float,
    confidence: float,
    cost_of_error: float | None = None,
    *,
    policy_violation: bool = False,
    min_scale: float = 0.2,
    max_scale: float = 1.0,
) -> tuple[float, float]:
    """Derive a conservative adapter learning rate from operational risk."""
    current_risk = risk_score(
        confidence,
        cost_of_error,
        policy_violation=policy_violation,
    )
    scale = min(max(1.0 - current_risk, min_scale), max_scale)
    return base_learning_rate * scale, current_risk


def agem_project(new_gradient: Sequence[float], reference_gradient: Sequence[float]) -> np.ndarray:
    """Project a candidate gradient onto the A-GEM feasible half-space."""
    g_new = np.asarray(new_gradient, dtype=float)
    g_ref = np.asarray(reference_gradient, dtype=float)
    if g_new.shape != g_ref.shape:
        raise ValueError("new_gradient and reference_gradient must share the same shape")
    if g_new.size == 0:
        return g_new

    dot = float(np.dot(g_new, g_ref))
    if dot >= 0.0:
        return g_new

    denom = float(np.dot(g_ref, g_ref)) + 1e-12
    return g_new - ((dot / denom) * g_ref)


def compute_cfs(before_scores: dict[str, float], after_scores: dict[str, float]) -> float:
    """Compute a catastrophic forgetting score over shared domains."""
    shared_domains = sorted(set(before_scores).intersection(after_scores))
    if not shared_domains:
        return 0.0

    penalties: list[float] = []
    for domain in shared_domains:
        before = before_scores[domain]
        after = after_scores[domain]
        if before <= 0.0 or after >= before:
            penalties.append(0.0)
            continue
        penalties.append((before - after) / max(before, 1e-12))
    return float(sum(penalties) / len(penalties))


def centroid_distance_projection(embeddings: Sequence[Sequence[float]]) -> np.ndarray:
    """Project embeddings onto their distance-to-centroid scalar manifold."""
    matrix = np.asarray(list(embeddings), dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        return np.asarray([], dtype=float)
    centroid = matrix.mean(axis=0)
    return np.linalg.norm(matrix - centroid, axis=1)


def population_stability_index(
    reference: Sequence[float] | np.ndarray,
    current: Sequence[float] | np.ndarray,
    *,
    bins: int = 10,
) -> float:
    """Compute PSI between two scalar distributions."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.size == 0 or cur.size == 0:
        return 0.0

    percentiles = np.linspace(0, 100, bins + 1)
    edges = np.percentile(ref, percentiles)
    edges = np.unique(edges)
    if len(edges) < 2:
        min_edge = float(ref.min(initial=0.0))
        max_edge = float(ref.max(initial=0.0)) + 1e-6
        edges = np.asarray([min_edge, max_edge], dtype=float)

    ref_hist, _ = np.histogram(ref, bins=edges)
    cur_hist, _ = np.histogram(cur, bins=edges)
    ref_dist = ref_hist / max(ref_hist.sum(), 1)
    cur_dist = cur_hist / max(cur_hist.sum(), 1)

    epsilon = 1e-6
    ref_dist = np.where(ref_dist == 0.0, epsilon, ref_dist)
    cur_dist = np.where(cur_dist == 0.0, epsilon, cur_dist)
    return float(np.sum((cur_dist - ref_dist) * np.log(cur_dist / ref_dist)))


def ks_2samp(
    reference: Sequence[float] | np.ndarray,
    current: Sequence[float] | np.ndarray,
) -> tuple[float, float]:
    """Approximate the two-sample Kolmogorov-Smirnov statistic and p-value."""
    ref = np.sort(np.asarray(reference, dtype=float))
    cur = np.sort(np.asarray(current, dtype=float))
    if ref.size == 0 or cur.size == 0:
        return 0.0, 1.0

    data = np.sort(np.concatenate([ref, cur]))
    ref_cdf = np.searchsorted(ref, data, side="right") / ref.size
    cur_cdf = np.searchsorted(cur, data, side="right") / cur.size
    statistic = float(np.max(np.abs(ref_cdf - cur_cdf)))

    effective_n = math.sqrt((ref.size * cur.size) / (ref.size + cur.size))
    lam = (effective_n + 0.12 + (0.11 / max(effective_n, 1e-6))) * statistic
    if lam <= 0.0:
        return statistic, 1.0

    series = 0.0
    for term in range(1, 6):
        series += ((-1) ** (term - 1)) * math.exp(-2.0 * (term**2) * (lam**2))
    p_value = min(max(2.0 * series, 0.0), 1.0)
    return statistic, p_value
