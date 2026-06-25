# [C5-REAL] Exergy-Maximized
"""
Causal Graph Engine for CORTEX Audit System.
Maintains the Keyed Retrieval Graph System (KRGS) and causal linkages for deterministic replay.
"""

import json
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class CausalNode:
    event_id: str
    trace_id: str
    span_id: str
    parent_event_id: Optional[str]
    type: str # "execution" | "state_change" | "io" | "error"
    side_effects: list[str]
    derived_state_hashes: list[str]
    payload_hash: str
    
    def canonical_json(self) -> str:
        # sorted keys for deterministic hashing
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))

class CausalDAG:
    """In-memory reconstruction of the event DAG for replay tracking."""
    def __init__(self):
        self.nodes: dict[str, CausalNode] = {}
        self.edges: dict[str, list[str]] = {} # parent_event_id -> list[event_id]
        
    def add_node(self, node: CausalNode):
        self.nodes[node.event_id] = node
        if node.parent_event_id:
            if node.parent_event_id not in self.edges:
                self.edges[node.parent_event_id] = []
            self.edges[node.parent_event_id].append(node.event_id)
            
    def get_children(self, event_id: str) -> list[str]:
        return self.edges.get(event_id, [])
        
    def rebuild_from_stream(self, event_stream: list[dict]):
        """Reconstructs the DAG from a JSONL event stream."""
        for evt in event_stream:
            node = CausalNode(
                event_id=evt["event_id"],
                trace_id=evt["trace_id"],
                span_id=evt["span_id"],
                parent_event_id=evt.get("parent_hash"),
                type=evt["type"],
                side_effects=evt.get("side_effects", []),
                derived_state_hashes=evt.get("derived_state_hashes", []),
                payload_hash=evt["event_hash"]
            )
            self.add_node(node)

    def compute_merkle_rollup(self, root_event_id: str) -> int:
        from cortex.engine.fable_out import hash_distance_rollup

        # Simplified deterministic distances based on topological depth
        distances = []
        queue = [(root_event_id, 0)]
        visited = set()
        
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            
            distances.append(depth * 10)  # Convert topological depth to causal distance
            
            for child_id in self.get_children(node_id):
                if child_id not in visited:
                    queue.append((child_id, depth + 1))
        
        # We need an integer representation of the root hash to seed the Fable Rollup
        root_int = int(root_event_id, 16) % (2**32 - 1)
        return hash_distance_rollup(root_int, distances)

    def get_ancestors(self, event_id: str) -> set[str]:
        """Returns the set of all ancestor event IDs (lineage)."""
        ancestors = set()
        queue = [event_id]
        while queue:
            curr = queue.pop(0)
            if curr not in self.nodes:
                continue
            parent = self.nodes[curr].parent_event_id
            if parent and parent not in ancestors:
                ancestors.add(parent)
                queue.append(parent)
        return ancestors

    def compute_causal_distance(self, event_a_id: str, event_b_id: str) -> float:
        """
        BABYLON-60 (Fase 4): Content Addressed Cognition.
        Computes the structural causal distance between two nodes based on their topological lineage overlap.
        Distance = 1.0 - (Intersection(Ancestors_A, Ancestors_B) / Union(Ancestors_A, Ancestors_B))
        Returns 0.0 for identical lineage, 1.0 for completely disjoint lineage.
        """
        if event_a_id == event_b_id:
            return 0.0
            
        ancestors_a = self.get_ancestors(event_a_id)
        ancestors_b = self.get_ancestors(event_b_id)
        
        # Include the node themselves in their ancestry
        ancestors_a.add(event_a_id)
        ancestors_b.add(event_b_id)
        
        intersection = ancestors_a.intersection(ancestors_b)
        union = ancestors_a.union(ancestors_b)
        
        if not union:
            return 1.0
            
        jaccard_similarity = len(intersection) / len(union)
        return 1.0 - jaccard_similarity
