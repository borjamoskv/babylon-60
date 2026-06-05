import numpy as np
from typing import List, Tuple
from cortex.interfaces.memory_provider import MemoryNode

class CoherenceScorer:
    """
    Measures if the subgraph makes 'human sense'.
    coherence = density(causal_edges) + embedding_consistency - temporal_noise
    """
    
    @staticmethod
    def score(nodes: List[MemoryNode], edges: List[Tuple[str, str, float]]) -> float:
        if not nodes:
            return 0.0
            
        N = len(nodes)
        
        # 1. Edge density
        possible_edges = N * (N - 1)
        density = len(edges) / possible_edges if possible_edges > 0 else 1.0
        
        # 2. Embedding consistency (average pairwise cosine similarity)
        consistency = 0.0
        if N > 1:
            sims = []
            for i in range(N):
                for j in range(i + 1, N):
                    e1 = nodes[i].embedding
                    e2 = nodes[j].embedding
                    if isinstance(e1, (list, np.ndarray)) and isinstance(e2, (list, np.ndarray)):
                        v1 = np.array(e1)
                        v2 = np.array(e2)
                        n1 = np.linalg.norm(v1)
                        n2 = np.linalg.norm(v2)
                        if n1 > 0 and n2 > 0:
                            sim = np.dot(v1, v2) / (n1 * n2)
                            sims.append(float(sim))
            if sims:
                consistency = sum(sims) / len(sims)
        else:
            consistency = 1.0
            
        # 3. Temporal noise (variance in timestamps)
        temporal_noise = 0.0
        if N > 1:
            timestamps = [n.timestamp for n in nodes if n.timestamp > 0]
            if len(timestamps) > 1:
                # Normalize std dev by mean to get a relative noise factor
                std_dev = np.std(timestamps)
                mean_t = np.mean(timestamps)
                temporal_noise = float(std_dev / mean_t) if mean_t > 0 else 0.0
                # Cap noise penalty
                temporal_noise = min(temporal_noise, 0.5)
                
        coherence = density + consistency - temporal_noise
        
        # Normalize to [0, 1] roughly
        return max(0.0, min(1.0, coherence / 2.0))
