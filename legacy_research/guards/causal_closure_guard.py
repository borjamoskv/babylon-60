# [C5-REAL] Exergy-Maximized
"""CORTEX - Causal Closure Guard (Axiom VIII: Stochastic Obsolescence).

Enforces strict thermodynamic causality across the execution boundary.
Eliminates synthetic token-cost thresholds and regex-based artifact heuristics 
in favor of deterministic cryptographic verification of `ClosurePayload`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

from cortex.types.evidence import ClosurePayload

logger = logging.getLogger("cortex.guards.causal_closure")

# Retained strictly for legacy pipeline migrations. Must be deprecated.
@dataclass
class SwarmProposal:
    agent_id: str
    mission_statement: str
    content: str
    token_cost: int = 0


class CausalClosureGuard:
    """Enforces Axiom VIII: Massive execution must yield verifiable causal condensation."""

    def __init__(self) -> None:
        # min_token_threshold is permanently eradicated. Causality is absolute.
        pass

    def verify_closure(self, payload: ClosurePayload) -> bool:
        """Evaluates if the execution achieved causal closure.

        Args:
            payload: The explicitly structured analytical output tied to evidence.

        Raises:
            RuntimeError: SAGA-1 Abort if the evidence payload is inconsistent.

        Returns:
            bool: True if safe to persist.
        """
        expected_dict = {
            "claims": payload.claims,
            "evidence_hash": payload.evidence.evidence_hash,
            "verdict": payload.verdict
        }
        encoded = json.dumps(expected_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        computed_hash = hashlib.sha3_256(encoded).hexdigest()

        if computed_hash != payload.payload_hash:
            logger.error(
                "🛑 [P0] Causal Closure Failure! "
                "The computed payload hash does not match the sealed payload_hash. "
                "Evidence tampering or semantic drift detected."
            )
            raise RuntimeError(
                "[P0] AX-VIII Violation: Failed to achieve Causal Closure. "
                "Structural payload hash mismatch."
            )

        # Validate that the evidence bundle has actually been populated
        if not payload.evidence.sources and not payload.claims:
            logger.error("🛑 [P0] Causal Closure Failure! Empty claims and evidence.")
            raise RuntimeError(
                "[P0] AX-VIII Violation: Payload contains no observable evidence or claims."
            )

        logger.info("Causal Closure verified. Epistemic chain intact.")
        return True

    def verify_legacy_closure(self, proposal: SwarmProposal) -> bool:
        """Bridge for legacy swarm pipelines. Fails instantly if content is pure prose."""
        if not proposal.content.strip():
            logger.warning("[%s] Empty legacy proposal.", proposal.agent_id)
            return False
            
        has_ledger = "CORTEX-TAINT" in proposal.content or "LedgerPayload" in proposal.content
        if not has_ledger:
            raise RuntimeError(
                f"[P0] AX-VIII Violation: Agent {proposal.agent_id} failed to achieve Causal Closure. "
                f"Legacy Swarm output must contain permanent invariants."
            )
             
        return True
