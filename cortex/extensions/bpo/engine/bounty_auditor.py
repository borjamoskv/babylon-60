"""
BOUNTY-AUDITOR: Agente de Ejecución de Strikes de Seguridad
Especializado en la auditoría de código y ejecución de exploits nativos.
"""

import asyncio
import logging

from scripts.hybrid_router import route_target

from .negotiator_agent import BPONegotiatorAgent

logger = logging.getLogger("BOUNTY-AUDITOR")


class BountyAuditorAgent(BPONegotiatorAgent):
    """
    Agente L1 para la ejecución de auditorías de seguridad.
    Transforma el 'Alpha' detectado en 'Yield' (Bounty) mediante Strikes.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def _negotiate(self, opportunity: dict):
        """
        Sobrescribe la negociación con un Strike Híbrido (P-Mode: Performance/Price).
        Usa el HybridRouter para decidir entre Strike Rápido o Hound Profundo.
        """
        opp_id = opportunity.get("id")
        project_name = opportunity.get("payload", {}).get("project_name")
        exergy = opportunity.get("exergy_potential", 0.0)

        logger.info("⚔️ [FLASH-ENGINE] INICIANDO AUDITORÍA HÍBRIDA: %s", project_name)

        # 1. Ejecutar mediante Hybrid Router
        # El router se encarga de: Strike (Rust) -> Decision -> Hound (Python/LLM)
        try:
            # Sync wrapper for the router logic
            f_state = route_target(
                title=opportunity.get("payload", {}).get("project_name"),
                url=opportunity.get("payload", {}).get("github_url"),
                exergy=exergy,
            )

            if f_state and f_state.get("is_verified", False):
                # Emitir evento para la cristalización del reporte (REPORT-Ω)
                await self.bus.emit(
                    event_type="bpo:intelligence_crystallized",
                    payload={
                        "opp_id": opp_id,
                        "project": project_name,
                        "mode": "P-FLASH",
                        "intelligence_state": {
                            "hypotheses": f_state.get("hypotheses", []),
                            "proof_of_concept": f_state.get("proof_of_concept", ""),
                            "target_code": f_state.get("target_code", ""),
                        },
                    },
                    source=self.id,
                    routing_key="report_engine",
                )

            logger.info("✅ [LEÓN] Ciclo Híbrido Completado: %s", opp_id)
            await self.bus.emit(
                event_type="bpo:execution_success",
                payload={"opp_id": opp_id, "project": project_name, "mode": "P-FLASH"},
                source=self.id,
                routing_key="wealth_ledger",
            )
        except Exception as e:
            logger.error("❌ Fallo en Hybrid-Strike: %s", e)


if __name__ == "__main__":

    async def run_auditor():
        auditor = BountyAuditorAgent("auditor-gamma-01")
        await auditor.start_listening()

    try:
        asyncio.run(run_auditor())
    except KeyboardInterrupt:
        pass
