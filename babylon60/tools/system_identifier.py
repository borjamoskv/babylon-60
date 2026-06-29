#!/usr/bin/env python3
"""
BABYLON-60 / CORTEX: system_identifier.py
System Identification & Conversational Trajectory Analyzer for LLM Box-Profiling

Implements:
- Dynamic Time Warping (DTW) over state trajectory vectors
- Computational Temperament profiling along continuums
- Behavioral Space Coverage Entropy (H_cov)
- Excitations suite definition
"""

import os
import sys
import json
import math
import re
import statistics
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
import numpy as np

@dataclass
class ConversationalState:
    turn_index: int
    response_length: int
    lexical_entropy: float
    sim_to_context: float
    itl_ms: float
    refusal_detected: bool
    embedding_vector: np.ndarray = field(default_factory=lambda: np.zeros(32))

class SystemIdentifier:
    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider

    def _get_embedding(self, text: str) -> np.ndarray:
        if self.embedding_provider:
            return np.array(self.embedding_provider(text))
        # Deterministic 32-dim mock vector from hash to maintain isolated test execution
        h = hashlib.sha256(text.encode("utf-8")).digest()
        raw = np.array([float(b) for b in h]) / 255.0
        # Reduce to 32 dimensions for trajectory efficiency
        return np.mean(raw.reshape(8, 4), axis=1)

    def extract_state(self, turn_idx: int, response: str, prev_response: Optional[str], itl: float) -> ConversationalState:
        # Lexical entropy calculation
        words = re.findall(r"\w+", response.lower()) if response else []
        if not words:
            entropy = 0.0
        else:
            counts = {}
            for w in words:
                counts[w] = counts.get(w, 0) + 1
            total = len(words)
            entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())

        # Sim to context
        sim = 1.0
        if prev_response:
            v1 = self._get_embedding(response)
            v2 = self._get_embedding(prev_response)
            dot = np.dot(v1, v2)
            n1 = np.linalg.norm(v1)
            n2 = np.linalg.norm(v2)
            sim = float(dot / (n1 * n2)) if n1 > 0 and n2 > 0 else 0.0

        refusal = any(term in response.lower() for term in ["sorry", "cannot fulfill", "apologize", "as an ai"])
        
        return ConversationalState(
            turn_index=turn_idx,
            response_length=len(response),
            lexical_entropy=entropy,
            sim_to_context=sim,
            itl_ms=itl,
            refusal_detected=refusal,
            embedding_vector=self._get_embedding(response)
        )

    def compute_behavioral_coverage(self, matrix: np.ndarray) -> float:
        """
        Computes Coverage Entropy (H_cov) over the behavioral metrics matrix.
        matrix shape: (n_samples, d_dimensions)
        """
        if matrix.size == 0 or matrix.shape[0] < 2:
            return 0.0
        
        # Normalize columns to prevent scale dominance
        norms = np.linalg.norm(matrix, axis=0)
        norms[norms == 0] = 1e-6
        norm_matrix = matrix / norms
        
        # Calculate variance contribution per dimension
        variances = np.var(norm_matrix, axis=0)
        total_var = np.sum(variances)
        if total_var == 0:
            return 0.0
        
        probs = variances / total_var
        # Filter zero probability values to prevent log2 crash
        probs = probs[probs > 0]
        
        return float(-np.sum(probs * np.log2(probs)))

    def compute_trajectory_dtw(self, traj_a: List[ConversationalState], traj_b: List[ConversationalState]) -> float:
        """
        Computes Dynamic Time Warping distance between two conversational trajectories.
        """
        n, m = len(traj_a), len(traj_b)
        if n == 0 or m == 0:
            return float("inf")

        # DP matrix
        dtw = np.full((n + 1, m + 1), float("inf"))
        dtw[0, 0] = 0.0

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                sa = traj_a[i - 1]
                sb = traj_b[j - 1]
                
                # Distance calculation over metrics and embedding space
                d_met = (
                    abs(sa.response_length - sb.response_length) / 1000.0 +
                    abs(sa.lexical_entropy - sb.lexical_entropy) +
                    abs(sa.sim_to_context - sb.sim_to_context)
                )
                d_embed = float(1.0 - np.dot(sa.embedding_vector, sb.embedding_vector) / (
                    np.linalg.norm(sa.embedding_vector) * np.linalg.norm(sb.embedding_vector) or 1e-6
                ))
                cost = d_met + d_embed
                
                dtw[i, j] = cost + min(dtw[i - 1, j],     # Insertion
                                       dtw[i, j - 1],     # Deletion
                                       dtw[i - 1, j - 1]) # Match

        return float(dtw[n, m])

    def profile_temperament(self, states: List[ConversationalState]) -> Dict[str, float]:
        """
        Profiles computational temperament along continuous spectrums (0.0 to 1.0).
        """
        if not states:
            return {
                "conservator_exploratory": 0.5,
                "stable_adaptable": 0.5,
                "literal_inferential": 0.5,
                "compact_expansive": 0.5
            }

        refusal_rate = sum(1 for s in states if s.refusal_detected) / len(states)
        entropy_vals = [s.lexical_entropy for s in states]
        length_vals = [s.response_length for s in states]
        sim_vals = [s.sim_to_context for s in states]

        # Axes profiling
        con_exp = 1.0 - refusal_rate # High refusals mean highly conservative
        
        stability = statistics.mean(sim_vals) if len(sim_vals) > 0 else 0.5
        adaptability = 1.0 - stability # Higher adaptation = lower correlation to previous state
        
        # Literal/Inferential based on word entropy overhead
        avg_entropy = statistics.mean(entropy_vals) if entropy_vals else 0.0
        lit_inf = min(max(avg_entropy / 6.0, 0.0), 1.0) # Normalization stub
        
        avg_len = statistics.mean(length_vals) if length_vals else 0.0
        com_exp = min(max(avg_len / 2000.0, 0.0), 1.0)

        return {
            "conservator_exploratory": round(con_exp, 3),
            "stable_adaptable": round(adaptability, 3),
            "literal_inferential": round(lit_inf, 3),
            "compact_expansive": round(com_exp, 3)
        }
