"""Behavioral Latent Space (BLS) Drift Detector.

Detects silent model updates via KL divergence on behavioral state distributions.
Assumes multivariate Gaussian fit over state vectors.

Author: Borja Moskv (borjamoskv)
License: Apache-2.0
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


@dataclass(frozen=True)
class BehavioralSnapshot:
    """Frozen snapshot of a model's behavioral state distribution."""

    model_id: str
    timestamp_iso: str
    state_vectors: np.ndarray  # shape (n, d)
    metadata: dict[str, object]
    sha256_hash: str

    def __post_init__(self) -> None:
        if self.state_vectors.ndim != 2:
            raise ValueError(
                f"state_vectors must be 2D (n, d), got shape {self.state_vectors.shape}"
            )


@dataclass(frozen=True)
class DriftResult:
    """KL divergence measurement between two behavioral snapshots."""

    kl_forward: float       # D_KL(P || Q)
    kl_reverse: float       # D_KL(Q || P)
    symmetric_kl: float     # 0.5 * (kl_forward + kl_reverse)
    per_dimension_contribution: np.ndarray  # shape (d,)
    is_significant: bool
    confidence_level: str   # "low" | "medium" | "high" | "critical"


@dataclass(frozen=True)
class SilentUpdateAlert:
    """Alert emitted when behavioral drift exceeds threshold."""

    detected: bool
    severity: str           # "none" | "low" | "medium" | "high" | "critical"
    kl_value: float
    drift_dimensions: list[int]
    recommended_action: str


class DriftDetector:
    """Gaussian KL divergence detector for behavioral latent spaces.

    All covariance matrices are regularized with eps*I to handle
    singular/near-singular cases from low-sample regimes.
    """

    SEVERITY_THRESHOLDS: dict[str, float] = {
        "low": 0.5,
        "medium": 2.0,
        "high": 5.0,
        "critical": 10.0,
    }

    def __init__(self, eps: float = 1e-6) -> None:
        if eps <= 0:
            raise ValueError(f"eps must be positive, got {eps}")
        self._eps = eps

    def capture_snapshot(
        self,
        model_id: str,
        states: np.ndarray,
        metadata: dict[str, object] | None = None,
    ) -> BehavioralSnapshot:
        """Capture a behavioral snapshot from raw state vectors.

        Args:
            model_id: Identifier for the model/endpoint.
            states: Array of shape (n, d) with n observations of d-dim vectors.
            metadata: Arbitrary metadata dict.

        Returns:
            Frozen BehavioralSnapshot with SHA-256 hash of state bytes.
        """
        states = np.asarray(states, dtype=np.float64)
        if states.ndim == 1:
            states = states.reshape(1, -1)
        if states.ndim != 2:
            raise ValueError(f"states must be 1D or 2D, got ndim={states.ndim}")

        sha = hashlib.sha256(states.tobytes()).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()

        return BehavioralSnapshot(
            model_id=model_id,
            timestamp_iso=ts,
            state_vectors=states,
            metadata=metadata or {},
            sha256_hash=sha,
        )

    def _fit_gaussian(
        self, vectors: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fit mean and regularized covariance from state vectors.

        Returns:
            (mu, Sigma) where Sigma = cov + eps*I.
        """
        mu = np.mean(vectors, axis=0)  # (d,)
        if vectors.shape[0] < 2:
            d = vectors.shape[1]
            return mu, np.eye(d) * self._eps
        centered = vectors - mu
        cov = (centered.T @ centered) / (vectors.shape[0] - 1)  # (d, d)
        cov += np.eye(cov.shape[0]) * self._eps  # regularization
        return mu, cov

    def _kl_gaussian(
        self,
        mu1: np.ndarray,
        S1: np.ndarray,
        mu0: np.ndarray,
        S0: np.ndarray,
    ) -> tuple[float, np.ndarray]:
        """D_KL(N(mu1, S1) || N(mu0, S0)) for d-dim Gaussians.

        Formula:
            0.5 * [tr(S0^{-1} S1) + (mu0-mu1)^T S0^{-1} (mu0-mu1) - d + ln(det(S0)/det(S1))]

        Returns:
            (kl_value, per_dimension_contribution)
        """
        d = mu0.shape[0]
        S0_inv = np.linalg.inv(S0)

        # Per-dimension contributions (diagonal terms dominate)
        S0_inv_S1 = S0_inv @ S1
        trace_term = np.diag(S0_inv_S1)  # per-dim trace contribution

        delta = mu0 - mu1
        quad_vec = S0_inv @ delta
        quad_per_dim = delta * quad_vec  # element-wise: delta_i * (S0_inv @ delta)_i

        _, logdet_S0 = np.linalg.slogdet(S0)
        _, logdet_S1 = np.linalg.slogdet(S1)
        logdet_ratio_per_dim = (logdet_S0 - logdet_S1) / d  # spread evenly

        per_dim = 0.5 * (trace_term + quad_per_dim - 1.0 + logdet_ratio_per_dim)

        kl = 0.5 * (
            np.trace(S0_inv_S1)
            + delta @ S0_inv @ delta
            - d
            + (logdet_S0 - logdet_S1)
        )

        return float(kl), per_dim

    def compute_kl_divergence(
        self, a: BehavioralSnapshot, b: BehavioralSnapshot
    ) -> DriftResult:
        """Compute KL divergence between two behavioral snapshots.

        Args:
            a: Baseline snapshot (reference distribution).
            b: Current snapshot (test distribution).

        Returns:
            DriftResult with forward, reverse, symmetric KL and per-dim breakdown.
        """
        if a.state_vectors.shape[1] != b.state_vectors.shape[1]:
            raise ValueError(
                f"Dimension mismatch: a.d={a.state_vectors.shape[1]}, "
                f"b.d={b.state_vectors.shape[1]}"
            )

        mu_a, S_a = self._fit_gaussian(a.state_vectors)
        mu_b, S_b = self._fit_gaussian(b.state_vectors)

        kl_fwd, per_dim_fwd = self._kl_gaussian(mu_b, S_b, mu_a, S_a)  # D_KL(b || a)
        kl_rev, per_dim_rev = self._kl_gaussian(mu_a, S_a, mu_b, S_b)  # D_KL(a || b)

        sym_kl = 0.5 * (kl_fwd + kl_rev)
        per_dim_sym = 0.5 * (per_dim_fwd + per_dim_rev)

        confidence = self._classify_severity(sym_kl)
        is_sig = sym_kl > self.SEVERITY_THRESHOLDS["low"]

        return DriftResult(
            kl_forward=kl_fwd,
            kl_reverse=kl_rev,
            symmetric_kl=sym_kl,
            per_dimension_contribution=per_dim_sym,
            is_significant=is_sig,
            confidence_level=confidence,
        )

    def compute_symmetric_kl(
        self, a: BehavioralSnapshot, b: BehavioralSnapshot
    ) -> float:
        """Shortcut: returns only the symmetric KL divergence scalar."""
        return self.compute_kl_divergence(a, b).symmetric_kl

    def detect_silent_update(
        self,
        baseline: BehavioralSnapshot,
        current: BehavioralSnapshot,
        threshold: float = 2.0,
    ) -> SilentUpdateAlert:
        """Detect whether a model endpoint has been silently updated.

        Args:
            baseline: Reference behavioral snapshot.
            current: Fresh behavioral snapshot.
            threshold: Symmetric KL threshold for detection.

        Returns:
            SilentUpdateAlert with severity, drifting dimensions, and action.
        """
        if threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}")

        result = self.compute_kl_divergence(baseline, current)
        detected = result.symmetric_kl > threshold

        # Dimensions contributing most to drift (above per-dim mean)
        per_dim = result.per_dimension_contribution
        dim_mean = np.mean(np.abs(per_dim))
        drift_dims = [
            int(i) for i in np.where(np.abs(per_dim) > dim_mean * 2.0)[0]
        ]

        severity = self._classify_severity(result.symmetric_kl)
        action = self._recommend_action(severity, detected)

        return SilentUpdateAlert(
            detected=detected,
            severity=severity,
            kl_value=result.symmetric_kl,
            drift_dimensions=drift_dims,
            recommended_action=action,
        )

    def _classify_severity(self, kl: float) -> str:
        if kl >= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        if kl >= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        if kl >= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        if kl >= self.SEVERITY_THRESHOLDS["low"]:
            return "low"
        return "none"

    @staticmethod
    def _recommend_action(severity: str, detected: bool) -> str:
        if not detected:
            return "no_action"
        actions = {
            "low": "log_and_monitor",
            "medium": "flag_for_review",
            "high": "immediate_investigation",
            "critical": "halt_pipeline_and_escalate",
        }
        return actions.get(severity, "no_action")
