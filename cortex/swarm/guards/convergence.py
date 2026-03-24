import asyncio
import logging
from datetime import datetime, timezone

from cortex.ledger import SovereignLedger

logger = logging.getLogger("cortex.swarm.guards.convergence")

class ConvergenceGuards:
    """
    State Drift Detection & Convergence (Ω-Sync).
    Ensures that parallel agents in the swarm maintain a unified truth.
    """

    def __init__(self, ledger: SovereignLedger | None = None, drift_threshold: float = 0.3):
        self.ledger = ledger
        self.drift_threshold = drift_threshold
        self._global_state_hash: str | None = None
        self._last_sync = datetime.now(timezone.utc)

    def _emit_ledger_event(self, *, action: str, detail: dict[str, str]) -> None:
        if self.ledger is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("ConvergenceGuards: No running loop, skipping ledger event '%s'", action)
            return
        loop.create_task(
            self.ledger.record_transaction(
                project="swarm",
                action=action,
                detail=detail,
            )
        )

    def validate_state(self, agent_id: str, local_state_hash: str) -> bool:
        """
        Check if an agent's local state has drifted from the global consensus.
        """
        if not self._global_state_hash:
            self._global_state_hash = local_state_hash
            return True

        if local_state_hash != self._global_state_hash:
            logger.warning(
                "ConvergenceGuards: Drift detected in agent '%s' (Ω-Drift)", agent_id
            )
            self._emit_ledger_event(
                action="drift_detected",
                detail={
                    "agent_id": agent_id,
                    "global_hash": self._global_state_hash or "",
                    "local_hash": local_state_hash,
                },
            )
            return False

        return True

    def synchronize(self, consensus_hash: str) -> None:
        """Force a global synchronization point."""
        logger.info("ConvergenceGuards: Synchronizing global state to %s", consensus_hash)
        self._global_state_hash = consensus_hash
        self._last_sync = datetime.now(timezone.utc)
        self._emit_ledger_event(
            action="global_convergence",
            detail={"consensus_hash": consensus_hash},
        )
