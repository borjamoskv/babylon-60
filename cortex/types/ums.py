# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "UmsHeader",
    "UmsVectorReference",
    "UmsThermodynamics",
    "UmsPayload",
    "UmsProof",
    "UniversalMemorySchema",
]


class UmsHeader(BaseModel):
    agent_did: str
    owner_did: str
    transaction_id: str
    timestamp: int


class UmsVectorReference(BaseModel):
    hash: str
    dimensions: int = 1536


class UmsThermodynamics(BaseModel):
    stochastic_entropy_in: float
    deterministic_exergy_out: float
    half_life_seconds: int = 2592000


class UmsPayload(BaseModel):
    block_id: str
    type: str
    content: str
    confidence: float
    vector_reference: UmsVectorReference
    thermodynamics: UmsThermodynamics


class UmsProof(BaseModel):
    zk_merkle_root: str
    signature: str


class UniversalMemorySchema(BaseModel):
    ums_version: str = "1.0.0"
    header: UmsHeader
    payload: UmsPayload
    proof: UmsProof
