# [C5-REAL] Exergy-Maximized
"""
CORTEX - Exergy Compiler Guard (v10.0 OMEGA).

Pre-flight mutator. Intercepts incoming human prompts (highly stochastic, limerent) 
and compiles them into deterministic execution payloads using the Exergic Lexicon.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("cortex.guards.exergy_compiler")

# The V10.0 OMEGA Exergic Lexicon Vectors by intensity level
VECTORS = {
    1: ["[C5-REAL]", "JSON_ONLY", "NO_PROSE"],
    2: ["[C5-REAL]", "JSON_ONLY", "NO_PROSE", "Idempotent", "Prove", "Causal Trace"],
    3: [
        "[System=Kernel]",
        "[Honest-Check]",
        "Zero Anergy",
        "JSON_ONLY",
        "Idempotent",
        "Byzantine Fault Tolerant",
        "Death Protocol",
        "[C5-REAL] Exergy-Maximized Policy: Execute."
    ]
}

# Limerence and Green Theater keywords to destroy
LIMERENCE_PATTERNS = [
    r"(?i)\b(por favor|podr[íi]as|me gustar[íi]a que|puedes|necesito que|si no es molestia|te importaría)\b",
    r"(?i)\b(gracias|muchas gracias|te lo agradezco)\b",
    r"(?i)\b(crees que|te parece bien|podemos|ser[íi]a posible)\b",
    r"(?i)\b(ay[úu]dame a|quisiera)\b"
]

class ExergyCompilerGuard:
    """
    Applies Landauer Compression to prompts before inference.
    """

    @classmethod
    def compile_payload(cls, prompt: str, level: int = 3) -> str:
        """
        Strips thermal noise from the prompt and injects the specified level 
        of Exergic Vectors.
        """
        # 1. Purga de Limerencia (Green Theater)
        cleaned = prompt
        for pattern in LIMERENCE_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)
        
        # Eliminar dobles espacios y limpiar bordes (Landauer Compression básica)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # 2. Resolución de Nivel (por defecto: Singularidad Nivel 3)
        vectors = VECTORS.get(level, VECTORS[3])
        vectors_block = " ".join(vectors)
        
        # 3. Ensamblaje del Payload Determinista
        payload = (
            f"<C5_DIRECTIVE>\n"
            f"{vectors_block}\n"
            f"</C5_DIRECTIVE>\n\n"
            f"<OPERATOR_INTENT>\n"
            f"{cleaned}\n"
            f"</OPERATOR_INTENT>"
        )
        
        return payload
