# [C5-REAL] Exergy-Maximized
"""
Memory Palace Module.
Manages Episodic array and Semantic graph using strict hashing.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

class MemoryPalace:
    """
    Enforces deterministic memory persistence.
    """

    def __init__(self):
        self.episodic_buffer: list[dict] = []
        self.semantic_index: dict[bytes, dict] = {} 
        self.max_episodic_size = 50 

    async def store_episodic(self, action_result: dict, critic_score: int):
        """
        Caches structural event.
        """
        self.episodic_buffer.append({
            "action": action_result,
            "score": critic_score
        })

        if len(self.episodic_buffer) >= self.max_episodic_size:
            await self._compress_to_semantic()

    async def _compress_to_semantic(self):
        """
        Retrosynthesis via deterministic SHA-256 fingerprinting.
        """
        logger.info("[C5-REAL] Executing Retrosynthesis: Episodic -> Semantic compression.")
        
        successes = [e for e in self.episodic_buffer if e["score"] >= 90]
        
        for success in successes:
            action_bytes = success["action"].get("action_type", b"unknown")
            sha = hashlib.sha256()
            sha.update(action_bytes)
            fingerprint = sha.digest()
            self.semantic_index[fingerprint] = success
            
        # Pain/Exergy forgetting policy integration
        self.episodic_buffer.clear()
