import logging
import re
from typing import Optional

logger = logging.getLogger("cortex.guards")

DECORATIVE_TERMS = [
    r"por supuesto", r"entendido", r"como un modelo de lenguaje",
    r"espero que te sea útil", r"aquí tienes", r"en conclusión",
    r"procedo a explicarte", r"estoy aquí para ayudarte"
]

def calculate_exergy(text: str) -> float:
    """Calculates thermodynamic yield (exergy) of a string."""
    if not text.strip():
        return 0.0
    
    text_lower = text.lower()
    matches = []
    for term in DECORATIVE_TERMS:
        if re.search(term, text_lower):
            matches.append(term)
            
    if not matches:
        return 1.0
        
    # Penalty based on decorative density
    penalty = (len(matches) * 0.2)
    score = max(0.0, 1.0 - penalty)
    
    # Very short text that is decorative is 0
    if len(text.split()) < 10 and matches:
        return 0.0
        
    return score

class ExergyGuard:
    """Ω₂: The Thermodynamic Guard. Filters low-exergy (decorative) content."""
    
    def check_thermodynamic_yield(
        self, 
        content: str, 
        project_id: str, 
        fact_type: str = "knowledge"
    ) -> float:
        """Enforces exergy limits on knowledge/decision facts."""
        # Non-text or structured types bypass exergy checks (assumed high utility)
        if fact_type in ("code", "structure", "archive"):
            return 1.0
            
        score = calculate_exergy(content)
        if score < 0.5:
            logger.warning("Ω₂ Violation: Low exergy content detected (%.2f)", score)
            raise ValueError(
                f"Thermodynamic Violation: Ingestion of low-exergy decorative content rejected (Score: {score:.2f}). "
                "CORTEX requires high exergy/utility density."
            )
            
        return score
