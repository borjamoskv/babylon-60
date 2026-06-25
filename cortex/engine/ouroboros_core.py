# [C5-REAL] Exergy-Maximized
"""
OUROBOROS-CORE - Python implementation of the Epistemic Dependency Graph (EDG)
Replaces the Rust `cortex_rs/src/edg.rs` to fix LOC constraints and sqlite_vec issues.
"""

from enum import Enum
from typing import Optional


class ValidationStatus(str, Enum):
    """
    ValidationStatus measures the epistemic certainty of a fact or node.
    """
    Proven = "Proven"
    Inferred = "Inferred"
    Speculative = "Speculative"
    Challenged = "Challenged"
    Contradicted = "Contradicted"

    @classmethod
    def from_legacy(cls, value: str) -> "ValidationStatus":
        mapping = {
            "Accepted": cls.Proven,
            "Invalid": cls.Contradicted,
            "Deprecated": cls.Contradicted,
            "Proven": cls.Proven,
            "Inferred": cls.Inferred,
            "Speculative": cls.Speculative,
            "Challenged": cls.Challenged,
            "Contradicted": cls.Contradicted,
        }
        return mapping.get(value, cls.Speculative)


class RetrievalNode:
    """Canonical Retrieval Graph Node."""
    
    def __init__(self, node_id: str, confidence: float):
        self.id: str = node_id
        self.status: ValidationStatus = ValidationStatus.Proven
        self.confidence: float = confidence
        self.supported_by: set[str] = set()
        self.supports: set[str] = set()
        self.exergy: float = 0.0
        self.rul_claim_id: Optional[str] = None

    def get_supported_by(self) -> list[str]:
        return list(self.supported_by)

    def get_supports(self) -> list[str]:
        return list(self.supports)


class ExergyMutation:
    def __init__(self, node_id: str, delta: float, rul_claim_id: Optional[str] = None):
        self.node_id = node_id
        self.delta = delta
        self.rul_claim_id = rul_claim_id


class ExergyError(Exception):
    pass


class ExergyGuard:
    def __init__(self, cluster_size: int, max_delta_per_epoch: float):
        self.cluster_size = cluster_size
        self.max_delta_per_epoch = max_delta_per_epoch

    def validate(self, mutation: ExergyMutation, valid_nodes: list[str]) -> None:
        if mutation.node_id not in valid_nodes:
            raise ExergyError(f"NodeNotFound: {mutation.node_id}")
        if abs(mutation.delta) > self.max_delta_per_epoch:
            raise ExergyError(f"Delta exceeds maximum per epoch: {mutation.delta}")


class RetrievalGraph:
    """Canonical Retrieval Graph in Python."""
    
    def __init__(self):
        self.nodes: dict[str, RetrievalNode] = {}

    def add_node(self, node: RetrievalNode) -> None:
        self.nodes[node.id] = node

    def get_node_status(self, node_id: str) -> Optional[ValidationStatus]:
        node = self.nodes.get(node_id)
        return node.status if node else None

    def add_dependency(self, supporter_id: str, supported_id: str) -> None:
        supporter = self.nodes.get(supporter_id)
        if not supporter:
            raise KeyError(f"Node not found: {supporter_id}")
        
        supported = self.nodes.get(supported_id)
        if not supported:
            raise KeyError(f"Node not found: {supported_id}")

        supporter.supports.add(supported_id)
        supported.supported_by.add(supporter_id)

    def invalidate_node(self, node_id: str) -> list[str]:
        affected = []
        stack = [node_id]

        while stack:
            current_id = stack.pop()
            node = self.nodes.get(current_id)
            if node and node.status != ValidationStatus.Contradicted:
                node.status = ValidationStatus.Contradicted
                node.confidence = 0.0
                affected.append(current_id)
                # Propagate invalidation
                stack.extend(node.supports)
                
        return affected

    def apply_exergy_mutation(self, mutation: ExergyMutation, guard: ExergyGuard) -> None:
        valid_nodes = list(self.nodes.keys())
        guard.validate(mutation, valid_nodes)
        
        node = self.nodes.get(mutation.node_id)
        if node:
            node.exergy += mutation.delta
            if mutation.rul_claim_id is not None:
                node.rul_claim_id = mutation.rul_claim_id
        else:
            raise ExergyError(f"NodeNotFound: {mutation.node_id}")

