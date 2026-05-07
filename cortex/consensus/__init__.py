"""CORTEX v5.0 — Consensus.

Neural Swarm Consensus and Reputation-Weighted validation.
"""

from __future__ import annotations

from typing import Any

from cortex.consensus.manager import ConsensusManager

# Runtime optional loading for legacy extensions that may not be installed.
ReputationManager: Any = None
TrustGraph: Any = None
try:
    from cortex.consensus.reputation import ReputationManager as _RM  # pyright: ignore[reportMissingImports]

    ReputationManager = _RM
except ImportError:
    pass
try:
    from cortex.consensus.trust import TrustGraph as _TG  # pyright: ignore[reportMissingImports]

    TrustGraph = _TG
except ImportError:
    pass

__all__ = ["ConsensusManager", "ReputationManager", "TrustGraph"]
