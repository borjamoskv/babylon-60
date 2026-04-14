from __future__ import annotations

import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger("uvicorn.error")


class FactBatchStoreEngine(Protocol):
    """Minimal async store contract for batch fact ingestion."""

    async def store(
        self,
        *,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str],
        source: str | None,
        meta: dict[str, Any],
        parent_decision_id: int | None = None,
    ) -> int: ...


@dataclass(frozen=True)
class FactBatchStoreResult:
    """HTTP-neutral summary of a batch store operation."""

    stored: int
    ids: list[int]
    errors: list[dict[str, Any]]
    total_requested: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "stored": self.stored,
            "ids": self.ids,
            "errors": self.errors,
            "total_requested": self.total_requested,
        }


async def batch_store_facts(
    engine: FactBatchStoreEngine,
    *,
    memories: Sequence[dict[str, Any]],
    tenant_id: str,
) -> FactBatchStoreResult:
    """Store a batch of facts while preserving partial-success semantics."""
    ids: list[int] = []
    errors: list[dict[str, Any]] = []

    for index, memory in enumerate(memories):
        try:
            fact_id = await engine.store(
                project=memory["project"],
                content=memory["content"],
                tenant_id=tenant_id,
                fact_type=memory["type"],
                tags=memory["tags"],
                source=memory.get("source"),
                meta=memory.get("metadata") or {},
                parent_decision_id=memory.get("parent_decision_id"),
            )
            ids.append(fact_id)
        except (sqlite3.Error, ValueError, OSError):
            logger.exception("Failed to batch store fact at index %d", index)
            errors.append({"index": index, "error": "Failed to store fact"})

    return FactBatchStoreResult(
        stored=len(ids),
        ids=ids,
        errors=errors,
        total_requested=len(memories),
    )
