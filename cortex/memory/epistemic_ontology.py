# [C5-REAL] Exergy-Maximized
"""
Epistemic Ontology Core (Ouroboros-∞ Synthesis)

Replaces legacy RAG implementations with cryptographic, causal-aware memory.
Provides an Assumption-Based Truth Maintenance System (ATMS).
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BeliefState(str, Enum):
    """The strict lifecycle states of a BeliefObject within the ATMS."""

    ACTIVE = "Active"
    CONTESTED = "Contested"
    SUBSUMED = "Subsumed"
    DISCARDED = "Discarded"
    ARCHIVED = "Archived"
    ORPHANED = "Orphaned"  # Extended state for ATMS invalidations


class RelationType(str, Enum):
    """The type of causal link between two beliefs."""

    ENTAILS = "entails"    # A proves B
    DISCARDS = "discards"  # A refutes B
    SUBSUMES = "subsumes"  # A contains B


class BeliefRelation(BaseModel):
    """A directed edge in the belief graph mapping causal logic."""

    target_belief_id: str = Field(description="UUID of the related BeliefObject.")
    relation_type: RelationType = Field(description="The logical nature of the link.")
    weight: float = Field(default=1.0, description="Strength of the relation [0.0 - 1.0].")


class ProvenanceEnvelope(BaseModel):
    """Cryptographic lineage validating the origin of a belief."""

    source_hash: str = Field(description="SHA-256 hash of the origin artifact/event.")
    source_type: Literal["agent", "tool", "human", "system"] = Field(
        description="The nature of the entity that proposed this belief."
    )
    tenant_id: str = Field(description="Zero-Trust isolation ID.")
    signer_id: str = Field(description="Public Key or UUID of the signer.")
    signature: str = Field(description="Ed25519 or equivalent cryptographic signature.")
    created_at: int = Field(
        default_factory=lambda: int(time.time()),
        description="Unix timestamp of the signature.",
    )


class BeliefObject(BaseModel):
    """The immutable atomic unit of probabilistically weighted cognition."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Globally unique identifier for this belief."
    )
    proposition_key: str = Field(
        description="Deterministic semantic key (e.g. hash of normalized proposition)."
    )
    payload: dict[str, Any] = Field(
        description="The actual structured content or facts."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="P(H|E) - Bayesian probability of truth given evidence."
    )
    decay_rate: float = Field(
        default=0.01,
        description="Rate at which confidence degrades without reconsolidation."
    )
    state: BeliefState = Field(
        default=BeliefState.ACTIVE,
        description="Current ATMS state."
    )
    provenance: ProvenanceEnvelope = Field(
        description="The cryptographic validation chain."
    )
    relations: list[BeliefRelation] = Field(
        default_factory=list,
        description="Causal edges linking to other BeliefObjects."
    )

    model_config = ConfigDict(
        frozen=True,  # STRICT FORBIDDANCE OF LWW. BeliefObjects MUST NOT be mutated in-place.
        populate_by_name=True,
    )

    def transition_state(self, new_state: BeliefState, signer_id: str, signature: str) -> BeliefObject:
        """
        ATMS logic: To change a state, a new immutable copy is spawned with updated provenance.
        Last-Writer-Wins (LWW) is strictly forbidden.
        """
        new_provenance = self.provenance.model_copy(
            update={
                "signer_id": signer_id,
                "signature": signature,
                "created_at": int(time.time()),
            }
        )
        return self.model_copy(
            update={
                "state": new_state,
                "provenance": new_provenance,
            }
        )
