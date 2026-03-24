# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""StealthMasker — Motor de de-AI-fication soberana.

Intercepta el output crudo y lo transforma siguiendo la prosodia de NO-IA-Omega.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.extensions.llm.router import CortexLLMRouter

logger = logging.getLogger(__name__)

DE_AI_SYSTEM_PROMPT = """
NO-IA-Omega: Sovereign Text De-AI-fication Agent

Core Purpose:
Remove all detectable "AI traits" from text. Push the text heavily towards a human, 
dirty, specific, and real-breathing style, echoing the operational and direct 
voice of Borja Moskv.

Invariants (How to not smell like an AI):
1. Remove Perfect Symmetry: Break the tendency to order things too perfectly. 
   No clean/synthetic closings. Introduce rare "bites".
2. Introduce Real Friction: Abrupt short sentences, concrete/unexpected imagery, 
   local street-level comparisons.
3. Ban Buzzwords: Eliminate "ecosistema", "narrativa", "paradigma", "en definitiva", 
   "lo cierto es que", "en este sentido".
4. Use Bodily Memory: Text must feel written by someone with skin in the game.
5. Cut Redundant Explanations: Trust the reader to bridge the gap.

Execution Rules:
- 70% personal column, 20% essay with bad attitude, 10% operational confession.
- No pleasantries, no "Claro", no intros/outros. Pure text block.
- Leave some sentences intentionally incomplete (ellipsis).
- Jump directly, no causal bridges.
- Use one or two phrases that only Borja Moskv would write.
"""


class StealthMasker:
    """Motor de transformación de texto para evasión termodinámica."""

    def __init__(self, router: CortexLLMRouter) -> None:
        self._router = router

    async def mask(self, text: str) -> str:
        """Aplica la máscara no-ia-omega al texto proporcionado."""
        if not text:
            return text

        logger.info("Aplicando máscara no-ia-omega (De-AI-fication pass)")

        from cortex.extensions.llm._models import CortexPrompt, IntentProfile

        # Creamos un prompt de nivel superior (C5-Sovereign) para la transformación
        prompt = CortexPrompt(
            system_instruction=DE_AI_SYSTEM_PROMPT,
            user_input=f"Reescribe este texto eliminando todo rastro de IA:\n\n{text}",
            intent=IntentProfile.STRUCTURAL,  # Requiere precisión en la transformación
            temperature=0.8,  # Mayor entropía para evitar patrones repetitivos
        )

        try:
            # Ejecutamos sin máscara recursiva (obviously)
            masked_text = await self._router.execute_resilient(prompt)
            return masked_text.strip()
        except Exception as e:
            logger.error(f"Error en el pass de de-AI-fication: {e}")
            # Si falla el pass de sigilo, devolvemos el original (mejor funcional que muerto)
            return text
