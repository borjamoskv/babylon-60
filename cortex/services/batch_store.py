import logging
import sqlite3
from typing import Any

from cortex.auth import AuthResult
from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger(__name__)

async def execute_batch_store(
    req: Any,
    auth: AuthResult,
    engine: AsyncCortexEngine,
    item_type_label: str,
) -> dict:
    """Consolidated helper to batch store memories/facts."""
    ids: list[int] = []
    errors: list[dict] = []
    for i, mem in enumerate(req.memories):
        try:
            fact_id = await engine.store(
                project=mem.project,
                content=mem.content,
                tenant_id=auth.tenant_id,
                fact_type=mem.type,
                tags=mem.tags,
                source=mem.source,
                meta=mem.metadata or {},
                parent_decision_id=mem.parent_decision_id,
            )
            ids.append(fact_id)
        except (sqlite3.Error, ValueError, OSError):
            logger.exception("Failed to batch store %s at index %d", item_type_label, i)
            errors.append({"index": i, "error": f"Failed to store {item_type_label}"})

    return {
        "stored": len(ids),
        "ids": ids,
        "errors": errors,
        "total_requested": len(req.memories),
    }
