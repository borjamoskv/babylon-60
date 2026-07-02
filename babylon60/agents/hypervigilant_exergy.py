# [C5-REAL] Exergy-Maximized
"""Hypervigilant Exergy Agent.

Garantes continuous maximization of exergy across the system.
Monitors execution boundaries, purges anergy, and enforces C5-REAL constraints.
"""

import asyncio
import logging

from babylon60.agents.base import BaseAgent
from babylon60.agents.bus import MessageBus
from babylon60.agents.manifest import AgentManifest
from babylon60.agents.state import AgentStatus

logger = logging.getLogger("babylon60.agents.hypervigilant_exergy")

class HypervigilantExergyAgent(BaseAgent):
    """Daemon that enforces maximum exergy extraction and strict zero-anergy principles."""

    def __init__(
        self, manifest: AgentManifest, bus: MessageBus, vigilance_interval_seconds: float = 5.0
    ) -> None:
        super().__init__(manifest, bus)
        self.vigilance_interval_seconds = vigilance_interval_seconds
        self._vigilance_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Starts the hypervigilant daemon."""
        await super().start()
        if not self._vigilance_task:
            self._vigilance_task = asyncio.create_task(self._vigilance_loop())

    async def stop(self) -> None:
        """Stops the daemon."""
        if self._vigilance_task:
            self._vigilance_task.cancel()
            try:
                await self._vigilance_task
            except asyncio.CancelledError:
                pass
            self._vigilance_task = None
        await super().stop()

    async def _vigilance_loop(self) -> None:
        """Continuous background loop for Exergy Maximization."""
        logger.info(
            f"[{self.manifest.agent_id}] Hypervigilant Exergy Agent started. Interval: {self.vigilance_interval_seconds}s"
        )
        while True:
            try:
                await asyncio.sleep(self.vigilance_interval_seconds)
                await self._enforce_exergy()
            except asyncio.CancelledError:
                logger.info(f"[{self.manifest.agent_id}] Hypervigilant Exergy Agent stopped.")
                break
            except Exception as e:  # noqa: BLE001
                logger.error(f"[{self.manifest.agent_id}] Exergy enforcement error: {e}")
                # Prevent silent thread death # noqa: BLE001

    async def _enforce_exergy(self) -> None:
        """Executes strict exergy audits and anergy purging."""
        if self.state.status == AgentStatus.STOPPED:
            return

        logger.info(
            f"[{self.manifest.agent_id}] ⚡ ENFORCING EXERGY MAXIMIZATION: Scanning system for thermodynamic rot."
        )

        # Weaponized Forgetting (Apoptosis Celular) - Ley Ω5
        if hasattr(self.bus, "purge_consumed"):
            try:
                deleted = await self.bus.purge_consumed()
                if deleted > 0:
                    logger.warning(
                        f"[{self.manifest.agent_id}] APOPTOSIS CELULAR: Purged {deleted} consumed messages. Anergy destroyed."
                    )
            except Exception as e: # noqa: BLE001
                # Fail-fast termodinámico
                logger.error(f"[{self.manifest.agent_id}] FRACTURA TERMODINAMICA: {e}")

        # Erradicación de Context Rot (Ley Ω2)
        if hasattr(self.memory, "facts") and len(self.memory.facts) > 100:
            logger.warning(f"[{self.manifest.agent_id}] CORTEX ROT DETECTED: Forcing causal collapse. Memory wiped.")
            self.memory.clear()


def create_hypervigilant_exergy_agent(
    name: str, bus: MessageBus, vigilance_interval_seconds: float = 5.0
) -> HypervigilantExergyAgent:
    """Factory for HypervigilantExergyAgent."""
    manifest = AgentManifest(
        agent_id=name,
        purpose="Hypervigilant enforcement of exergy maximization and zero-anergy execution.",
        can_delegate=False,
        daemon=True,
    )
    return HypervigilantExergyAgent(manifest, bus, vigilance_interval_seconds)
