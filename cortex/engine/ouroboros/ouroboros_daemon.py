"""
Ouroboros Daemon - Bucle GHOST_HUNT -> EXERGY_GATE -> STRIKE
"""

import asyncio
import logging

from cortex.engine.ouroboros.exergy_gate import ExergyGate
from cortex.engine.ouroboros.ghost_hunt import fetch_bounties
from cortex.engine.ouroboros.strike_actuator import StrikeActuator, StrikeVector
from cortex.engine_async import AsyncCortexEngine
from cortex.swarm.manager import SwarmManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ouroboros")


class OuroborosDaemon:
    def __init__(self):
        self.gate = ExergyGate()
        self.actuator = StrikeActuator(use_dry_run=False)  # Lived deployment
        self.engine = None
        self.swarm_manager = None

    async def initialize(self):
        from cortex import config
        from cortex.database.pool import CortexConnectionPool

        self.pool = CortexConnectionPool(config.DB_PATH, read_only=False)
        await self.pool.initialize()
        self.engine = AsyncCortexEngine(pool=self.pool, db_path=config.DB_PATH)
        self.swarm_manager = SwarmManager(ledger=self.engine._get_ledger())
        await self.swarm_manager.start_compaction(self.engine)
        logger.info("[OUROBOROS] Sovereign Engine & Compaction Initialized")

    async def shutdown(self):
        if self.swarm_manager:
            await self.swarm_manager.stop_compaction()
        if hasattr(self, "pool") and self.pool:
            await self.pool.close()

    async def ghost_hunt(self):
        """Dispara crawler autonomo vivo"""
        return await fetch_bounties()

    async def run_cycle(self):
        await self.initialize()
        try:
            targets = await self.ghost_hunt()
            for target in targets:
                gate_res = self.gate.evaluate_target(
                    target["expected_yield"], target["compute_cost"]
                )
                if gate_res["approved"]:
                    logger.info(
                        "[OUROBOROS] Target %s APPROVED: %s", target["id"], gate_res["reason"]
                    )
                    result = await self.actuator.strike(
                        StrikeVector.VECTOR_A_BOUNTY, target, self.swarm_manager
                    )
                    await self.ledger_write(result)
                else:
                    logger.info(
                        "[OUROBOROS] Target %s REJECTED: %s", target["id"], gate_res["reason"]
                    )
        except asyncio.CancelledError:
            logger.info("[OUROBOROS] Execution cancelled by shutdown.")
        finally:
            await self.shutdown()

    async def ledger_write(self, strike_result: dict):
        # AX-1000 Sovereign Integration into Master Ledger
        if self.engine:
            await self.engine.record_transaction(
                project="ouroboros",
                action="strike_execution",
                detail={
                    "yield": strike_result.get("net_yield", 0.0),
                    "cost": strike_result.get("compute_cost", 0.0),
                    "vector": strike_result.get("strike_vector", "unknown"),
                    "status": strike_result.get("status", "unknown"),
                    "session": strike_result.get("session_id", "none"),
                },
                tenant_id="default",
            )
        logger.info(
            "[LEDGER WRITE] Yield: $%s | Cost: $%s | Vector: %s | Status: %s",
            strike_result.get("net_yield", 0),
            strike_result.get("compute_cost", 0),
            strike_result.get("strike_vector", "unknown"),
            strike_result.get("status", "unknown"),
        )


if __name__ == "__main__":
    daemon = OuroborosDaemon()
    try:
        asyncio.run(daemon.run_cycle())
    except KeyboardInterrupt:
        logger.info("[OUROBOROS] Keyboard Interrupt. Process terminated safely.")
