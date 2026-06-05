from typing import Protocol, List, Tuple, Any
from dataclasses import dataclass, field
import numpy as np

@dataclass
class IntentVector:
    semantic_vector: np.ndarray | list[float]
    task_vector: np.ndarray | list[float]
    temporal_bias: float
    abstraction_level: float

@dataclass
class MemoryNode:
    id: str
    embedding: np.ndarray | list[float]
    fact_type: str
    timestamp: float
    causal_links: List[str] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)
    content: str = ""  # Populated ONLY during late hydration phase

@dataclass
class MemorySubgraph:
    root_query: str
    nodes: List[MemoryNode]
    edges: List[Tuple[str, str, float]]
    coherence_score: float

class MemoryProvider(Protocol):
    def embed(self, text: str) -> np.ndarray | list[float]:
        ...

    def search(self, query: str, limit: int = 10) -> List[MemoryNode]:
        ...

    def vector_search(self, embedding: np.ndarray | list[float], limit: int = 50) -> List[MemoryNode]:
        ...

    def neighbors(self, node_id: str) -> List[MemoryNode]:
        ...

    def causal_edges(self, node_id: str) -> List[Tuple[str, str, float]]:
        ...

    def hydrate(self, nodes: List[MemoryNode]) -> List[MemoryNode]:
        ...
