"""Pydantic models for bounty findings passed to the ledger bridge."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    C0_UNKNOWN = "C0-Unknown"
    C1_SPECULATIVE = "C1-Speculative"
    C2_WEAK = "C2-Weak"
    C3_HYPOTHETICAL = "C3-Hypothetical"
    C4_STRONG = "C4-Strong"
    C5_DETERMINISTIC = "C5-Deterministic"


class BountyPlatform(str, Enum):
    IMMUNEFI = "immunefi"
    HACKERONE = "hackerone"
    CODE4RENA = "code4rena"
    SHERLOCK = "sherlock"
    OPENAI = "openai"


class BountyFinding(BaseModel):
    """A confirmed vulnerability finding ready for ledger sealing."""

    vector_id: str = Field(..., description="Unique finding ID, e.g. 'SKY-Σ1-DUST'")
    protocol: str = Field(..., description="Target protocol, e.g. 'sky', 'ssv', 'lido'")
    contract: str = Field(default="", description="Vulnerable contract name")
    function: str = Field(default="", description="Vulnerable function signature")
    confidence: Confidence = Field(default=Confidence.C3_HYPOTHETICAL)
    finding: str = Field(..., description="Human-readable description of the vulnerability")
    severity: str = Field(default="medium", description="critical | high | medium | low")
    bounty_platform: BountyPlatform = Field(default=BountyPlatform.IMMUNEFI)
    max_bounty_usd: int = Field(default=0, description="Max bounty for the program")
    code_evidence: str = Field(default="", description="Source code reference")
    poc_path: str = Field(default="", description="Relative path to PoC file")
    seal: str = Field(default="", description="SHA-256 hex seal from swarm report")
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_ledger_dict(self) -> dict[str, Any]:
        """Serialize for EventLedgerL3 content field."""
        return self.model_dump(mode="json")
