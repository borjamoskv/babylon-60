"""MOSKV-1 — Tesseract Manifold.

4D Cognitive Manifold engine, implementing asynchronous convergence over
Perception, Decision, Creation, and Validation.
"""

from cortex.experimental.extensions.manifold.convergence import ConvergenceEngine
from cortex.experimental.extensions.manifold.models import (
    ConvergenceMetrics,
    DimensionalState,
    DimensionType,
    WaveState,
)

__all__ = [
    "ConvergenceEngine",
    "ConvergenceMetrics",
    "DimensionalState",
    "DimensionType",
    "WaveState",
]
