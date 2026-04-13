"""Compatibility shim for the legacy ``cortex.vsa_engine`` import surface."""

from __future__ import annotations

import numpy as np

from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory

__all__ = ["VSAEngine"]


class VSAEngine:
    """Minimal legacy adapter backed by the current HDC encoder stack.

    ``TensorGlialLegion`` still imports ``cortex.vsa_engine.VSAEngine``.
    The original module is gone, but its live contract is small: encode text
    into a dense vector and normalize arbitrary vectors. This adapter restores
    that surface without reintroducing a parallel VSA implementation.
    """

    def __init__(self, D: int = 8000, algebra: str = "HRR") -> None:
        self.D = D
        self.algebra = algebra
        self._encoder = HDCEncoder(ItemMemory(dim=D))

    def encode_text(self, text: str) -> np.ndarray:
        """Encode text into a float64 vector compatible with tensor buffers."""
        vector = self._encoder.encode_text(text).astype(np.float64, copy=False)
        return self.normalize(vector)

    def normalize(self, vector: np.ndarray) -> np.ndarray:
        """L2-normalize a vector while keeping zero vectors stable."""
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            return np.zeros(self.D, dtype=np.float64)
        return np.asarray(vector, dtype=np.float64) / norm
