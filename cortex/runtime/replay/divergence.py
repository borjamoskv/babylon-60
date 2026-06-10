# [C5-REAL] Exergy-Maximized
"""
Divergence Map — Metric Geometry over Execution Space

No es un debug tool.
Es un analizador del manifold de ejecuciones posibles.

Produce:
  1. Equivalence classes (runs con hash chains idénticas)
  2. Distance matrix (distancia entre trayectorias)
  3. Fork topology (punto exacto donde ejecuciones divergen)
  4. Entropy drift gradient (dirección de evolución del estado)

Propiedad:
  Si DivergenceMap.max_distance == 0 → sistema determinista demostrado
  Si DivergenceMap.max_distance > threshold → CI gate falla
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── Types ───────────────────────────────────────────────────────────

Trajectory = list[dict[str, Any]]  # list of snapshots from ReplayEngine.run()
HashChain = tuple[str, ...]


# ── State Distance ──────────────────────────────────────────────────

@dataclass(frozen=True)
class StateDistance:
    """Distancia métrica entre dos snapshots."""
    version: int
    hash_equal: bool
    key_jaccard: float        # 0.0 = identical keys, 1.0 = disjoint
    value_diff_ratio: float   # fraction of shared keys with different values
    composite: float          # single scalar distance

    @classmethod
    def compute(cls, snap_a: dict[str, Any], snap_b: dict[str, Any]) -> StateDistance:
        version = snap_a.get("version", -1)
        hash_eq = snap_a.get("state_hash") == snap_b.get("state_hash")

        data_a = snap_a.get("data", {})
        data_b = snap_b.get("data", {})

        keys_a = set(data_a.keys())
        keys_b = set(data_b.keys())
        union = keys_a | keys_b
        intersection = keys_a & keys_b

        if not union:
            key_jaccard = 0.0
        else:
            key_jaccard = 1.0 - len(intersection) / len(union)

        if not intersection:
            value_diff = 0.0
        else:
            diffs = sum(1 for k in intersection if data_a[k] != data_b[k])
            value_diff = diffs / len(intersection)

        # Composite: weighted combination. hash_equal dominates.
        composite = 0.0 if hash_eq else (0.5 * key_jaccard + 0.3 * value_diff + 0.2)

        return cls(
            version=version,
            hash_equal=hash_eq,
            key_jaccard=key_jaccard,
            value_diff_ratio=value_diff,
            composite=composite,
        )


# ── Fork Point ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class ForkPoint:
    """Punto exacto donde dos trayectorias divergen."""
    trajectory_a: int  # index
    trajectory_b: int  # index
    version: int       # version where divergence starts
    distance: StateDistance


# ── Entropy Drift ───────────────────────────────────────────────────

@dataclass(frozen=True)
class EntropyDrift:
    """Gradiente de complejidad del estado a lo largo de una trayectoria."""
    trajectory_index: int
    complexity_curve: tuple[int, ...]   # state size at each version
    gradient: tuple[float, ...]         # delta per step
    mean_gradient: float
    direction: str   # "expanding" | "stable" | "contracting"


# ── Equivalence Class ──────────────────────────────────────────────

@dataclass(frozen=True)
class EquivalenceClass:
    """Grupo de trayectorias con hash chains idénticas."""
    hash_chain: HashChain
    member_indices: tuple[int, ...]
    size: int


# ── Divergence Report ──────────────────────────────────────────────

@dataclass
class DivergenceReport:
    """Resultado completo del análisis de divergencia."""
    num_trajectories: int
    num_equivalence_classes: int
    equivalence_classes: list[EquivalenceClass]
    fork_points: list[ForkPoint]
    distance_matrix: list[list[float]]   # NxN symmetric
    entropy_drifts: list[EntropyDrift]
    max_distance: float
    is_deterministic: bool  # True iff all trajectories identical

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_trajectories": self.num_trajectories,
            "num_equivalence_classes": self.num_equivalence_classes,
            "equivalence_classes": [
                {"members": list(ec.member_indices), "size": ec.size}
                for ec in self.equivalence_classes
            ],
            "fork_points": [
                {
                    "a": fp.trajectory_a,
                    "b": fp.trajectory_b,
                    "version": fp.version,
                    "distance": fp.distance.composite,
                }
                for fp in self.fork_points
            ],
            "max_distance": self.max_distance,
            "is_deterministic": self.is_deterministic,
            "entropy_drifts": [
                {
                    "trajectory": ed.trajectory_index,
                    "mean_gradient": ed.mean_gradient,
                    "direction": ed.direction,
                }
                for ed in self.entropy_drifts
            ],
        }


# ── Divergence Map ──────────────────────────────────────────────────

class DivergenceMap:
    """
    Metric geometry over execution space.

    Takes N replay trajectories and produces:
    - equivalence classes
    - pairwise distance matrix
    - fork topology
    - entropy drift per trajectory
    """

    def __init__(self, trajectories: list[Trajectory]):
        if len(trajectories) < 2:
            raise ValueError("DivergenceMap requires at least 2 trajectories.")
        self.trajectories = trajectories

    def analyze(self, *, ci_threshold: float | None = None) -> DivergenceReport:
        """
        Ejecuta el análisis completo del manifold de ejecuciones.

        Args:
            ci_threshold: Si se provee, y max_distance > threshold,
                          levanta RuntimeError (CI gate mode).
        """
        n = len(self.trajectories)

        # 1. Extract hash chains
        chains = [self._extract_chain(t) for t in self.trajectories]

        # 2. Equivalence classes
        eq_classes = self._compute_equivalence_classes(chains)

        # 3. Distance matrix + fork points
        dist_matrix = [[0.0] * n for _ in range(n)]
        fork_points: list[ForkPoint] = []
        max_dist = 0.0

        for i in range(n):
            for j in range(i + 1, n):
                pair_dist, fork = self._compare_pair(i, j)
                dist_matrix[i][j] = pair_dist
                dist_matrix[j][i] = pair_dist
                max_dist = max(max_dist, pair_dist)
                if fork is not None:
                    fork_points.append(fork)

        # 4. Entropy drift
        drifts = [self._compute_drift(idx, t) for idx, t in enumerate(self.trajectories)]

        report = DivergenceReport(
            num_trajectories=n,
            num_equivalence_classes=len(eq_classes),
            equivalence_classes=eq_classes,
            fork_points=fork_points,
            distance_matrix=dist_matrix,
            entropy_drifts=drifts,
            max_distance=max_dist,
            is_deterministic=(len(eq_classes) == 1),
        )

        if ci_threshold is not None and max_dist > ci_threshold:
            raise RuntimeError(
                f"[CI GATE FAIL] Max divergence {max_dist:.6f} exceeds "
                f"threshold {ci_threshold:.6f}. "
                f"Fork points: {len(fork_points)}. "
                f"Equivalence classes: {len(eq_classes)}/{n}."
            )

        return report

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _extract_chain(trajectory: Trajectory) -> HashChain:
        return tuple(snap["state_hash"] for snap in trajectory)

    @staticmethod
    def _compute_equivalence_classes(chains: list[HashChain]) -> list[EquivalenceClass]:
        groups: dict[HashChain, list[int]] = {}
        for idx, chain in enumerate(chains):
            groups.setdefault(chain, []).append(idx)
        return [
            EquivalenceClass(
                hash_chain=chain,
                member_indices=tuple(members),
                size=len(members),
            )
            for chain, members in groups.items()
        ]

    def _compare_pair(self, i: int, j: int) -> tuple[float, ForkPoint | None]:
        t_a = self.trajectories[i]
        t_b = self.trajectories[j]
        max_len = max(len(t_a), len(t_b))

        distances: list[float] = []
        first_fork: ForkPoint | None = None

        for v in range(max_len):
            if v >= len(t_a) or v >= len(t_b):
                # Length mismatch — maximum distance for missing versions
                distances.append(1.0)
                if first_fork is None:
                    first_fork = ForkPoint(
                        trajectory_a=i,
                        trajectory_b=j,
                        version=v,
                        distance=StateDistance(
                            version=v, hash_equal=False,
                            key_jaccard=1.0, value_diff_ratio=1.0, composite=1.0,
                        ),
                    )
                continue

            sd = StateDistance.compute(t_a[v], t_b[v])
            distances.append(sd.composite)

            if not sd.hash_equal and first_fork is None:
                first_fork = ForkPoint(
                    trajectory_a=i, trajectory_b=j,
                    version=sd.version, distance=sd,
                )

        # Trajectory distance = max state distance (L∞ norm on execution manifold)
        return max(distances) if distances else 0.0, first_fork

    @staticmethod
    def _compute_drift(idx: int, trajectory: Trajectory) -> EntropyDrift:
        complexity = tuple(len(snap.get("data", {})) for snap in trajectory)

        if len(complexity) < 2:
            return EntropyDrift(
                trajectory_index=idx,
                complexity_curve=complexity,
                gradient=(),
                mean_gradient=0.0,
                direction="stable",
            )

        gradient = tuple(
            float(complexity[i] - complexity[i - 1])
            for i in range(1, len(complexity))
        )
        mean_grad = sum(gradient) / len(gradient) if gradient else 0.0

        if mean_grad > 0.1:
            direction = "expanding"
        elif mean_grad < -0.1:
            direction = "contracting"
        else:
            direction = "stable"

        return EntropyDrift(
            trajectory_index=idx,
            complexity_curve=complexity,
            gradient=gradient,
            mean_gradient=mean_grad,
            direction=direction,
        )
