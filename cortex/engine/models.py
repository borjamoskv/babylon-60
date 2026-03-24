"""CORTEX Engine — Fact Model and helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = ["Fact", "row_to_fact"]


@dataclass
class Fact:
    id: int
    tenant_id: str
    project: str
    content: str
    fact_type: str
    tags: list[str]
    meta: dict[str, Any]
    created_at: str
    updated_at: str
    is_tombstoned: bool = False
    is_quarantined: bool = False
    hash: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    source: str | None = None
    confidence: str = "C3"
    tx_id: int | None = None
    consensus_score: float = 1.0
    last_accessed: str | None = None
    cognitive_layer: str = "semantic"
    parent_decision_id: int | None = None

    def is_active(self) -> bool:
        """Evaluate logical validity using valid_until and physical state."""
        return not self.is_tombstoned and self.valid_until is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project": self.project,
            "content": self.content,
            "fact_type": self.fact_type,
            "type": self.fact_type,
            "tags": self.tags,
            "meta": self.meta,
            "active": self.is_active(),
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "source": self.source,
            "hash": self.hash,
            "tx_id": self.tx_id,
            "consensus_score": self.consensus_score,
            "last_accessed": self.last_accessed,
            "cognitive_layer": self.cognitive_layer,
            "parent_decision_id": self.parent_decision_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    r = list(row)
    while len(r) < 21:
        r.append(None)

    tenant_id = r[1] or "default"
    try:
        content = enc.decrypt_str(r[3], tenant_id=tenant_id) if r[3] else ""
    except ValueError:
        content = f"[ENCRYPTED — decryption failed] (fact #{r[0]})"

    # Safely handle JSON parsing
    try:
        tags = json.loads(r[5]) if r[5] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    try:
        meta = enc.decrypt_json(r[6], tenant_id=tenant_id) if r[6] else {}
    except ValueError:
        meta = {"error": "decryption_failed", "fact_id": r[0]}

    consensus_score = r[16]
    if consensus_score is None:
        consensus_score = meta.get("consensus_score", 1.0) if meta else 1.0

    tx_id = r[18]
    if tx_id is None and meta:
        tx_id = meta.get("tx_id")

    cognitive_layer = r[19]
    if not cognitive_layer:
        cognitive_layer = meta.get("cognitive_layer", "semantic") if meta else "semantic"

    parent_decision_id = r[20]
    if parent_decision_id is None and meta:
        parent_decision_id = meta.get("parent_decision_id")

    return Fact(
        id=r[0],
        tenant_id=tenant_id,
        project=r[2],
        content=content,  # type: ignore[reportArgumentType]
        fact_type=r[4],
        tags=tags,
        meta=meta,  # type: ignore[reportArgumentType]
        hash=r[7],
        valid_from=r[8],
        valid_until=r[9],
        source=r[10],
        confidence=r[11] or "C3",
        created_at=r[12],
        updated_at=r[13],
        is_tombstoned=bool(r[14]),
        is_quarantined=bool(r[15]),
        tx_id=tx_id,
        consensus_score=float(consensus_score),
        last_accessed=r[17],
        cognitive_layer=cognitive_layer,
        parent_decision_id=parent_decision_id,
    )
