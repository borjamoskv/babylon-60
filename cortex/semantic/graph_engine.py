from typing import List, Set, Dict, Tuple
from cortex.interfaces.memory_provider import MemoryNode, MemoryProvider

class GraphExpansionEngine:
    """
    Expands memory nodes by traversing causal links, temporal adjacency, and semantic similarity.
    """
    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    def expand(self, seeds: List[MemoryNode], hops: int = 2, causal_weight: float = 0.7) -> Tuple[List[MemoryNode], List[Tuple[str, str, float]]]:
        expanded_nodes: Dict[str, MemoryNode] = {node.id: node for node in seeds}
        edges: List[Tuple[str, str, float]] = []
        
        current_frontier = seeds
        for _ in range(hops):
            next_frontier = []
            for node in current_frontier:
                # Get causal neighbors
                causal_links = self.provider.causal_edges(node.id)
                for source_id, target_id, weight in causal_links:
                    edges.append((source_id, target_id, weight * causal_weight))
                    neighbor_id = target_id if source_id == node.id else source_id
                    
                    if neighbor_id not in expanded_nodes:
                        # Fetch the node
                        neighbors = self.provider.neighbors(neighbor_id)
                        if neighbors:
                            neighbor_node = neighbors[0]
                            expanded_nodes[neighbor_node.id] = neighbor_node
                            next_frontier.append(neighbor_node)
                            
            current_frontier = next_frontier
            if not current_frontier:
                break
                
        # Simple deduplication of edges
        unique_edges = list({(s, t): w for s, t, w in edges}.items())
        edges_out = [(s, t, w) for ((s, t), w) in unique_edges]
        
        return list(expanded_nodes.values()), edges_out
