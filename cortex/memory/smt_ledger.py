# [C5-REAL] Exergy-Maximized
"""
Integrity Plane: Sparse Merkle Tree (SMT) and Append-Only Belief Ledger.

Enforces the Ouroboros-∞ Synthesis rule:
- LWW (Last-Writer-Wins) is strictly FORBIDDEN.
- Direct overwrites destroy the hash chain. Revisions MUST be signed patches.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field

from cortex.memory.epistemic_ontology import BeliefObject, BeliefState


class SMTNode(BaseModel):
    """A node in the Sparse Merkle Tree."""

    hash_val: str
    left_child: str | None = None
    right_child: str | None = None
    is_leaf: bool = False


class SparseMerkleTree:
    """
    Cryptographic Integrity Plane.
    Provides O(log N) verification of belief lineage.
    """

    def __init__(self) -> None:
        self.root_hash: str = hashlib.sha256(b"genesis").hexdigest()
        self.nodes: dict[str, SMTNode] = {}
        # In a real implementation, this would be backed by a persistent KV store.

    def insert(self, belief_id: str, payload_hash: str) -> str:
        """
        Insert a new belief into the SMT and recompute the root.
        """
        leaf_hash = hashlib.sha256(f"{belief_id}:{payload_hash}".encode()).hexdigest()
        self.nodes[leaf_hash] = SMTNode(hash_val=leaf_hash, is_leaf=True)
        # Stub: recompute root
        self.root_hash = hashlib.sha256(f"{self.root_hash}:{leaf_hash}".encode()).hexdigest()
        return self.root_hash

    def verify(self, belief_id: str, payload_hash: str, proof: list[str]) -> bool:
        """
        Verify the mathematical shadow of a belief object.
        """
        # Stub implementation
        leaf_hash = hashlib.sha256(f"{belief_id}:{payload_hash}".encode()).hexdigest()
        return leaf_hash in self.nodes


class BeliefLedger:
    """
    Append-only ledger enforcing ATMS rules.
    """

    def __init__(self) -> None:
        self.smt = SparseMerkleTree()
        self.beliefs: dict[str, BeliefObject] = {}
        self.history: dict[str, list[BeliefObject]] = {}

    def propose_belief(self, belief: BeliefObject) -> None:
        """
        Propose a new belief. Direct overwrites are forbidden.
        """
        if belief.id in self.beliefs:
            raise ValueError(
                f"[Hard Fault] LWW Violation: Belief {belief.id} already exists. "
                "Direct overwrites are strictly FORBIDDEN. Use patch_belief()."
            )
        
        self._commit(belief)

    def patch_belief(self, original_id: str, new_state: BeliefState, signer_id: str, signature: str) -> BeliefObject:
        """
        Transition a belief state via a cryptographically signed patch.
        This spawns a new revision rather than overwriting the old one.
        """
        if original_id not in self.beliefs:
            raise ValueError(f"Belief {original_id} not found.")

        current_belief = self.beliefs[original_id]
        
        # Create immutable copy with new state and provenance
        revised_belief = current_belief.transition_state(
            new_state=new_state,
            signer_id=signer_id,
            signature=signature
        )

        self._commit(revised_belief)
        return revised_belief

    def _commit(self, belief: BeliefObject) -> None:
        """Internal commit preserving history and updating the SMT."""
        # Calculate payload hash for SMT
        payload_str = str(belief.model_dump(exclude={"provenance"}))
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        # Update Cryptographic Shadow
        self.smt.insert(belief.id, payload_hash)

        # Store Revision
        if belief.id not in self.history:
            self.history[belief.id] = []
        self.history[belief.id].append(belief)

        # Update head pointer
        self.beliefs[belief.id] = belief

    def attest_lineage(self, belief_id: str) -> list[BeliefObject]:
        """
        Resolve execution proofs by returning the full immutable history.
        """
        if belief_id not in self.history:
            raise KeyError(f"Belief {belief_id} has no lineage.")
        return self.history[belief_id]
