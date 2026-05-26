import logging
from collections.abc import Mapping
from typing import Any

from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.legion import AsyncSignalBus, SwarmAgent, SwarmSignal
from cortex.engine.exergy_optimizer import ExergyOptimizer

logger = logging.getLogger("cortex.exergy_agent")


class MockMetrics:
    """Mock metrics for Exergy calculation if not provided in context."""

    def __init__(self, active_children: int, uncertainty: float):
        self.active_children = active_children
        self.uncertainty = uncertainty


class ExergyMaximizerAgent:
    """
    Agente C5-REAL: Maximiza Exergía (Structure × Information - Entropy_paid).
    Aplica heurísticas O(1) para evaluar densidad del enjambre, latencia e incertidumbre,
    inyectando shocks metabólicos o forzando sharding cuando la entropía domina.
    """

    name = "exergy_maximizer_omega"

    async def optimize(self, target: str, context: Mapping[str, Any]) -> list[str]:
        findings = []
        logger.info("⚡ [EXERGY-MAXIMIZER] Evaluando fricción termodinámica en: %s", target)

        # Recuperar o simular métricas
        latency_ms = context.get("latency_ms", 25.0)
        active_children = context.get("active_children", 50)
        uncertainty = context.get("uncertainty", 0.3)
        max_capacity = context.get("max_capacity", 100)

        metrics = MockMetrics(active_children, uncertainty)

        # Cálculo O(1) de la Exergía (Densidad * Latencia * Incertidumbre)
        exergy_score = ExergyOptimizer.calculate_node_exergy(
            metrics, latency_ms=latency_ms, max_capacity=max_capacity
        )

        findings.append(f"[EXERGY SCORE] Calculado: {exergy_score:.4f}")

        if not ExergyOptimizer.is_thermally_stable(exergy_score):
            # Inyectar Dopamina para acelerar metabolismo y reducir latencia
            pulse_reason = (
                f"Exergy fell to {exergy_score:.4f} in {target}. Triggering metabolic optimization."
            )
            ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.6, reason=pulse_reason)
            findings.append(f"[OPTIMIZATION TRIGGERED] {pulse_reason}")

            if ExergyOptimizer.should_shard(exergy_score):
                findings.append(
                    "[SHARDING REQUIRED] Entropía insostenible detectada. Bifurcación de estado recomendada."
                )
        else:
            findings.append("[STABLE] Niveles de exergía óptimos. Fricción bajo control.")

        return findings


class ExergyAgentAdapter(SwarmAgent):
    """
    Wraps the ExergyMaximizerAgent into a SwarmAgent para el ecosistema CORTEX.
    """

    def __init__(self, agent_id: str, bus: AsyncSignalBus, engine: Any = None):
        super().__init__(agent_id, bus, engine)
        self.specialist = ExergyMaximizerAgent()

    async def execute(self, target: str) -> SwarmSignal:
        logger.warning("🔋 [EXERGY-MAXIMIZER] %s desplegado sobre: %s", self.agent_id, target)

        # Inyectando presión termodinámica sintética en la evaluación
        context = {
            "intent": "maximize_exergy",
            "agent_id": self.agent_id,
            "target": target,
            "latency_ms": 35.0,  # Alta latencia
            "active_children": 85,  # Alta densidad
            "uncertainty": 0.4,  # Incertidumbre media
        }

        try:
            findings = await self.specialist.optimize(target, context)
        except Exception as e:
            logger.error("Exergy maximization failed: %s", e)
            findings = [f"[CRITICAL FAILURE] {e}"]

        status = "VOID" if not findings else "SUCCESS"
        return SwarmSignal(
            agent_id=self.agent_id.upper() + "_EXERGY",
            target=target,
            status=status,
            payload={"findings": findings, "action": "entropy_reduction"},
            metrics={"found_count": len(findings)},
        )
