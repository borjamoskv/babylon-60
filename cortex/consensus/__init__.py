"""CORTEX v5.0 — Consensus.

Neural Swarm Consensus and Reputation-Weighted validation.
"""

from __future__ import annotations

from cortex.consensus.manager import ConsensusManager

__all__ = ["ConsensusManager"]

try:
    from cortex.consensus.reputation import ReputationManager
except ImportError:
    ReputationManager = None  # type: ignore[assignment]
else:
    __all__.append("ReputationManager")

try:
    from cortex.consensus.trust import TrustGraph
except ImportError:
    TrustGraph = None  # type: ignore[assignment]
else:
    __all__.append("TrustGraph")
