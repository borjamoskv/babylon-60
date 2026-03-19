"""CORTEX V8 - Swarm Continuity Verifier (LEGION-Ω)

Polls the SignalBus for Byzantine trust events and node death events,
persisting them as immutable facts in the cryptographic ledger.
"""

import logging
from typing import TYPE_CHECKING, Any

from cortex.extensions.signals.bus import AsyncSignalBus

if TYPE_CHECKING:
    from cortex.facts.manager import FactManager

logger = logging.getLogger("cortex.verification.swarm_continuity")


class SwarmContinuityVerifier:
    """Verifies and persists swarm continuity and trust events."""

    def __init__(self, bus: AsyncSignalBus, fact_manager: FactManager):
        self.bus = bus
        self.fact_manager = fact_manager
        self.consumer_id = "swarm_continuity"

    async def poll_and_verify(self, limit: int = 50) -> int:
        """Poll the signal bus for swarm events and persist them as facts."""
        processed = 0

        # Handled event types
        event_types = ["node:dead", "node:suspect", "trust:slash", "trust:reward"]

        for event_type in event_types:
            try:
                signals = await self.bus.poll(
                    event_type=event_type, consumer=self.consumer_id, limit=limit
                )

                for sig in signals:
                    await self._process_signal(sig)
                    processed += 1
            except Exception as e:
                logger.error("Error processing %s: %s", event_type, e)

        return processed

    async def _process_signal(self, sig: Any) -> None:
        payload = sig.payload
        project = sig.project or "CORTEX_SWARM"

        if sig.event_type in ("node:dead", "node:suspect"):
            content = f"Node {payload.get('node_id')} transitioned to {payload.get('new_status')} after {payload.get('elapsed_s')}s"
            confidence = "C5-Verified"  # Internal deterministic metric
            fact_type = "swarm_event"
        else:
            # trust:slash or trust:reward
            action = "slashed" if "slash" in sig.event_type else "rewarded"
            content = f"Node {payload.get('node_id')} {action}. New reputation: {payload.get('new_reputation')}. Reason: {payload.get('reason')}"
            confidence = "C0-Slashed" if "slash" in sig.event_type else "C5-Consensus"
            fact_type = "trust_score"

        # Store the fact
        await self.fact_manager.store(
            project=project,
            content=content,
            fact_type=fact_type,
            confidence=confidence,
            source="system",
            meta={"signal_id": sig.id, "payload": payload},
        )
