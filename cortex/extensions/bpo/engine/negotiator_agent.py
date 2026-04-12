"""
BPO-NEGOTIATOR: Agente de Ejecución Transaccional
Especializado en cerrar ciclos de valor (C5-REAL).
"""

import asyncio
import logging
import random

from cortex.engine.shared_bus import SovereignSharedBus

logger = logging.getLogger("BPO-NEGOTIATOR")


class BPONegotiatorAgent:
    """
    Agente L1 (Legion) para el cierre de operaciones.
    """

    def __init__(self, agent_id: str):
        self.id = agent_id
        self.bus = SovereignSharedBus(name="bpo_operations", create=False)

    async def start_listening(self):
        logger.info("🤝 NEGOTIATOR [%s] LISTENING: Esperando Alpha en el bus...", self.id)

        last_index = -1
        while True:
            signals = self.bus.poll(last_index)
            for idx, signal in signals:
                last_index = idx
                payload = signal.get("payload", {})
                if signal.get("event_type") != "bpo:alpha_detected":
                    if payload.get("event_type") != "bpo:alpha_detected":
                        continue
                    payload = payload.get("payload", payload)

                opportunity = payload
                logger.info(
                    "⚡ OPORTUNIDAD RECIBIDA: %s de %s", opportunity["id"], opportunity["source"]
                )
                await self._negotiate(opportunity)

            await asyncio.sleep(0.5)

    async def _negotiate(self, opportunity: dict):
        """
        Lógica de negociación/ejecución.
        Aplica la Ley Ω₂ (Termodinámica): El trabajo debe ser útil.
        """
        logger.info("🛠️ NEGOCIANDO: %s", opportunity["id"])

        # Simulación de pasos de negociación
        steps = ["OFFER_GEN", "RISK_VALIDATION", "TRANSACTION_EMIT"]
        for step in steps:
            logger.debug("[%s] Ejecutando fase: %s", opportunity["id"], step)
            await asyncio.sleep(0.05)

        success = random.random() > 0.2
        if success:
            logger.info("✅ NEGOCIACIÓN EXITOSA: Ciclo %s Cerrado", opportunity["id"])
            await self.bus.emit(
                event_type="bpo:execution_success",
                payload={"opp_id": opportunity["id"], "yield": 0.057},
                source=self.id,
                routing_key="wealth_ledger",
            )
        else:
            logger.warning("❌ NEGOCIACIÓN FALLIDA: %s", opportunity["id"])


if __name__ == "__main__":

    async def run_listener():
        negotiator = BPONegotiatorAgent("neg-01")
        await negotiator.start_listening()

    try:
        asyncio.run(run_listener())
    except KeyboardInterrupt:
        pass
