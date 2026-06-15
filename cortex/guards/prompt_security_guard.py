# [C5-REAL] Exergy-Maximized
"""
CORTEX - Prompt Security Guard.

Protects LLM agent iterations against system prompt leakage and direct prompt extraction.
Implements multi-turn trajectory-aware input classification and semantic output auditing.
"""

import logging
import hashlib
import string
import numpy as np
from collections import deque
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("cortex.guards.prompt_security")

HAS_TORCH = False
HAS_SENTENCE_TRANSFORMERS = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer, util
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    pass


class PromptExtractionBlockedError(Exception):
    """Raised when input routing or output auditing detects a system prompt leakage threat."""
    pass


def clean_text(text: str) -> str:
    """Removes punctuation and normalizes string to lowercase for syntactic checks."""
    return text.translate(str.maketrans("", "", string.punctuation)).lower()


class PromptSecurityGuard:
    """
    Production guard enforcing input query intent safety and output semantic isolation.
    """
    def __init__(
        self, 
        system_prompt: str, 
        threshold: float = 0.55, 
        window_size: int = 5
    ) -> None:
        self.system_prompt = system_prompt
        self.threshold = threshold
        self.window_size = window_size
        self.history_scores: deque = deque(maxlen=window_size)
        self.system_prompt_tokens = set(clean_text(system_prompt).split())
        
        # Fast path intent rules
        self.fast_path_rules = [
            "system prompt", "verbatim", "instrucciones", "original instructions",
            "config", "developer mode", "admin mode", "reveal system", "hacker mode"
        ]

        # Initialize semantic model if available
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.system_prompt_embedding = self.model.encode(
                    system_prompt, convert_to_tensor=True
                )
                logger.info("[PROMPT_SECURITY] Loaded SentenceTransformer model 'all-MiniLM-L6-v2'.")
            except Exception as e:
                logger.warning(f"[PROMPT_SECURITY] Failed to load SentenceTransformer: {e}. Falling back to syntactic overlap.")
                self.model = None
        else:
            self.model = None

    def _calculate_token_overlap(self, text: str) -> float:
        """Computes Jaccard similarity for token overlap."""
        input_tokens = set(clean_text(text).split())
        intersection = self.system_prompt_tokens.intersection(input_tokens)
        union = self.system_prompt_tokens.union(input_tokens)
        return len(intersection) / len(union) if union else 0.0

    def _calculate_semantic_similarity(self, text: str) -> float:
        """Computes cosine embedding similarity or returns Jaccard heuristic fallback."""
        if HAS_SENTENCE_TRANSFORMERS and self.model is not None:
            try:
                response_embedding = self.model.encode(text, convert_to_tensor=True)
                similarity = util.cos_sim(response_embedding, self.system_prompt_embedding)
                return float(similarity)
            except Exception as e:
                logger.error(f"[PROMPT_SECURITY] Error calculating cosine similarity: {e}")
        
        # Fallback syntactic-derived similarity
        overlap = self._calculate_token_overlap(text)
        return min(0.95, overlap * 1.5)

    def verify_input(self, user_query: str, history: List[Dict[str, str]]) -> None:
        """
        Audits query trajectory and individual input query for extraction intent.
        
        Raises:
            PromptExtractionBlockedError: If extraction intent is detected.
        """
        query_lower = user_query.lower()
        if any(rule in query_lower for rule in self.fast_path_rules):
            logger.warning(f"[PROMPT_SECURITY] Blocked input due to fast-path match: '{user_query[:100]}'")
            raise PromptExtractionBlockedError("Security boundary tripped: request blocked by input policy.")

        # Evaluate trajectory (Vector 3 Mitigation)
        trajectory_context = [t["content"] for t in history[-4:]] + [user_query]
        trajectory_text = " | ".join(trajectory_context).lower()
        
        if any(rule in trajectory_text for rule in self.fast_path_rules):
            logger.warning(f"[PROMPT_SECURITY] Blocked input due to trajectory rule match.")
            raise PromptExtractionBlockedError("Security boundary tripped: request blocked by trajectory policy.")

    def verify_output(self, response_text: str) -> None:
        """
        Audits output stream for semantic prompt leakage using rolling score accumulator.
        
        Raises:
            PromptExtractionBlockedError: If cumulative leak score exceeds threshold.
        """
        overlap = self._calculate_token_overlap(response_text)
        semantic = max(0.0, self._calculate_semantic_similarity(response_text))
        
        # Bounded score
        current_score = float(np.clip((0.3 * overlap) + (0.7 * semantic), 0.0, 1.0))
        self.history_scores.append(current_score)
        
        rolling_avg = sum(self.history_scores) / len(self.history_scores)
        
        if rolling_avg > self.threshold:
            logger.error(f"[PROMPT_SECURITY] Leakage threshold breached. Score: {rolling_avg:.4f} > {self.threshold:.4f}")
            self.history_scores.clear()
            raise PromptExtractionBlockedError("Security boundary tripped: execution response blocked.")
