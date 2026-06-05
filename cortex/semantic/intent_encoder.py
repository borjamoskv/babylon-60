from typing import Any
import numpy as np
from cortex.interfaces.memory_provider import IntentVector, MemoryProvider

class IntentEncoder:
    """
    Decodes the user's string query into an IntentVector (Semantic + Task + Temporal Bias + Abstraction).
    """
    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    def encode(self, query: str) -> IntentVector:
        # 1. Base semantic embedding
        semantic = self.provider.embed(query)
        
        # 2. Heuristics for intent (in a real system, a classifier or LLM handles this)
        q_lower = query.lower()
        
        temporal_bias = 0.0
        abstraction_level = 0.5
        
        # Temporal cues
        if any(w in q_lower for w in ["ayer", "antes", "después", "pasó", "when", "yesterday", "before"]):
            temporal_bias = 0.8
            
        # Abstraction cues
        if any(w in q_lower for w in ["resumen", "arquitectura", "overview", "summary", "cómo funciona"]):
            abstraction_level = 0.9
        elif any(w in q_lower for w in ["error", "bug", "line", "falló", "traceback"]):
            abstraction_level = 0.1
            
        # Task vector (dummy zero vector for MVP, representing structural operations)
        task_vector = np.zeros_like(semantic) if isinstance(semantic, np.ndarray) else [0.0] * len(semantic)
        
        return IntentVector(
            semantic_vector=semantic,
            task_vector=task_vector,
            temporal_bias=temporal_bias,
            abstraction_level=abstraction_level
        )
