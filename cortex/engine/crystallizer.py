# [C5-REAL] Exergy-Maximized
"""
CORTEX - Auto-Crystallizer (Project Aura-Omega).

Autonomous engine for refining "Thermal Noise" (low-exergy text) into
high-signal structural facts. Enforces Axiom Ω₁₃ by stripping
conversational padding.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.llm.manager import LLMManager

logger = logging.getLogger("cortex.engine.crystallizer")

CRYSTALLIZATION_PROMPT = """
SISTEMA: Eres un Cristalizador de Información de CORTEX (Axiom Ω₁₃).
TAREA: Transforma el ruido termal en un HECHO SOBERANO (Crystallized Fact).

REGLAS ESTRUCTURALES:
1. Elimina por completo el padding conversacional ("aquí tienes", "por supuesto", etc).
2. Conserva solo la lógica pura y las entidades técnicas.
3. No resumas; cristaliza. Mantén la precisión técnica al 100%.
4. Salida: Solo el texto refinado. Sin explicaciones.

RUIDO TERMAL:
{content}

HECHO CRISTALIZADO:
"""


class AutoCrystallizer:
    """Refines low-exergy text into high-signal structural facts."""

    def __init__(self, llm_manager: LLMManager) -> None:
        self._llm = llm_manager

    async def crystallize(self, content: str, model_tag: str = "frontier") -> str:
        """
        Refines the input content via a zero-shot LLM loop to maximize exergy.

        Args:
            content: The raw text with potential thermal noise.
            model_tag: The LLM tier to use (defaults to high-reasoning 'frontier').

        Returns:
            str: The refined, high-exergy fact.
        """
        logger.info("💎 [AURA-OMEGA] Crystallizing low-exergy fragment...")

        prompt = CRYSTALLIZATION_PROMPT.format(content=content)

        # Invoke the LLM with the crystallization instructions
        refined = await self._llm.generate(  # pyright: ignore[reportAttributeAccessIssue]
            prompt,
            model_tag=model_tag,
            temperature=0.0,  # Deterministic synthesis
            max_tokens=len(content) // 2 + 100,  # Enforce compression
        )

        refined = refined.strip()

        # If refinement failes or returns empty, fallback to raw but warn
        if not refined or len(refined) > len(content):
            logger.warning("⚠️ Crystallization failed to reduce entropy. Using raw content.")
            return content

        logger.info("✅ Fact crystallized: %d chars -> %d chars", len(content), len(refined))
        return refined

    async def purge_thermal_noise(self, conn) -> int:
        """
        O(1) TTL Purging (Axiom Ω₁₃).
        Automatically destroys any stochastic vectors in L1 memory that have not
        been cryptographically sealed (verified) within their time horizon (72h).
        No async daemons needed; invoked deterministically during the core loop.
        """
        try:
            cursor = await conn.execute(
                "DELETE FROM facts WHERE (taint_verified = 0 OR taint_verified IS NULL) AND "
                "(julianday('now') - julianday(created_at)) > 3.0"
            )
            await conn.commit()
            purged = cursor.rowcount
            if purged > 0:
                logger.warning("🧹 [AURA-OMEGA] Purged %d unverified stochastic vectors from L1 memory (O(1) TTL elapsed).", purged)
            return purged
        except Exception as e:
            logger.error("[AURA-OMEGA] O(1) Purge failed: %s", e)
            return 0
