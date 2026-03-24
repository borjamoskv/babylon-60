# This file is part of CORTEX. Apache-2.0.
# (c) 2026 CORTEX Swarm.

"""Autodidact Router — Dynamic complexity-aware routing (Ω₂ entropy split)."""

from __future__ import annotations

import logging
from enum import Enum

from cortex.extensions.llm._models import CortexPrompt, IntentProfile
from cortex.extensions.llm.router import CortexLLMRouter
from cortex.extensions.skills.autodidact.actuator import kolmogorov_ratio, shannon_entropy
from cortex.utils.result import Result

logger = logging.getLogger("cortex.extensions.llm.autodidact")


class ComplexityTier(Enum):
    """Clasificación de complejidad basada en métricas de información."""

    LOW = "low"
    OPTIMAL = "optimal"  # Borde del Caos
    HIGH = "high"
    ANOMALOUS = "anomalous"


class AutodidactRouter(CortexLLMRouter):
    """Extensión de CortexLLMRouter con análisis entrópico dinámico.

    Ajusta el IntentProfile y la estrategia de cascada basándose en la
    complejidad real del prompt (información útil vs ruido).
    """

    def _analyze_complexity(self, text: str) -> tuple[ComplexityTier, dict[str, float]]:
        """Calcula métricas y determina el tier de complejidad."""
        h = shannon_entropy(list(text))
        k = kolmogorov_ratio(text)

        metrics = {"h": h, "k": k, "len": len(text)}

        # Lógica del "Borde del Caos" (Ω₂ Autodidact-Ω)
        # Ajustado para evitar falsos positivos en strings cortos (noise vs complexity)
        if len(text) < 64:
            # Para strings cortos, K es poco fiable. Usamos solo H con umbral alto.
            if h > 5.0:
                tier = ComplexityTier.HIGH
            elif h > 3.8:
                tier = ComplexityTier.OPTIMAL
            else:
                tier = ComplexityTier.LOW
        else:
            if h > 7.5 or k < 0.05:
                tier = ComplexityTier.ANOMALOUS
            elif h > 5.5 or k > 0.6:
                tier = ComplexityTier.HIGH
            elif 4.0 <= h <= 5.5 and 0.15 <= k <= 0.45:
                tier = ComplexityTier.OPTIMAL
            else:
                tier = ComplexityTier.LOW

        return tier, metrics

    async def execute_resilient(self, prompt: CortexPrompt) -> Result[str, str]:
        """Override con análisis de complejidad dinámico."""
        # 1. Analizar el input del usuario (último mensaje o prompt completo)
        user_input = prompt.working_memory[-1]["content"] if prompt.working_memory else ""
        tier, metrics = self._analyze_complexity(user_input)

        logger.info(
            "🫁 [AUTODIDACT] Complexity: %s | H=%.2f | K=%.2f",
            tier.value, metrics["h"], metrics["k"]
        )

        # 2. Ajustar IntentProfile dinámicamente si no está forzado a algo específico
        # Si el prompt es muy complejo, elevamos la intención a REASONING o ARCHITECT
        original_intent = prompt.intent

        if tier == ComplexityTier.HIGH and original_intent == IntentProfile.GENERAL:
            logger.info("🚀 [ELEVATION] High complexity detected. Escalating to REASONING.")
            prompt.intent = IntentProfile.REASONING
        elif tier == ComplexityTier.OPTIMAL and original_intent == IntentProfile.GENERAL:
            logger.info("🌌 [OPTIMAL] Borde del Caos. Ensuring high-quality routing.")
            # Podríamos dejarlo en GENERAL pero asegurar que el fallback no sea local.
            pass
        elif tier == ComplexityTier.ANOMALOUS:
            logger.warning("☣️ [ANOMALOUS] Input suspicious or extremely high entropy.")
            # En modo soberano, podríamos filtrar o simplemente loguear.

        # 3. Ejecutar con la cascada estándar de CortexLLMRouter
        return await super().execute_resilient(prompt)

    def __repr__(self) -> str:
        return f"AutodidactRouter(primary={self._primary.provider_name})"
