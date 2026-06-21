# [C5-REAL] Exergy-Maximized
"""CORTEX - Causal Evidence Fundamentals.

Provides the foundational types that anchor the Epistemic Dependency Graph (EDG).
Eliminates stochastic evaluation (e.g., confidence floats) in favor of 
deterministic, hash-verifiable structural components.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Source:
    """Represents an immutable, verifiable data source."""
    uri: str
    content_hash: str
    metadata: dict


@dataclass(frozen=True)
class EvidenceBundle:
    """An atomic, causal wrapper around retrieved or generated evidence."""
    query: str
    sources: list[Source]
    retrieved_at: datetime
    evidence_hash: str

    @classmethod
    def forge(cls, query: str, sources: list[Source], retrieved_at: datetime) -> "EvidenceBundle":
        """Forges a new EvidenceBundle, deterministically computing the causal hash."""
        time_str = retrieved_at.isoformat()
        
        payload = {
            "query": query,
            "sources": [{"uri": s.uri, "content_hash": s.content_hash} for s in sources],
            "time": time_str
        }
        
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        evidence_hash = hashlib.sha3_256(encoded).hexdigest()
        
        return cls(
            query=query,
            sources=sources,
            retrieved_at=retrieved_at,
            evidence_hash=evidence_hash
        )


@dataclass(frozen=True)
class ClosurePayload:
    """The explicit structural payload replacing token-heuristics in Guard Evaluation.
    
    A verification layer produces this payload. The Guard consumes it and 
    strictly validates the continuity of the `evidence_hash`.
    """
    claims: list[dict]
    evidence: EvidenceBundle
    verdict: bool
    payload_hash: str

    @classmethod
    def seal(cls, claims: list[dict], evidence: EvidenceBundle, verdict: bool) -> "ClosurePayload":
        """Seals the analytical output linking it directly to its causal evidence."""
        payload = {
            "claims": claims,
            "evidence_hash": evidence.evidence_hash,
            "verdict": verdict
        }
        
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload_hash = hashlib.sha3_256(encoded).hexdigest()
        
        return cls(
            claims=claims,
            evidence=evidence,
            verdict=verdict,
            payload_hash=payload_hash
        )
