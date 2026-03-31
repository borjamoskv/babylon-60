from __future__ import annotations

from typing import Any

from cortex.extensions.security.guard_runtime import (
    BridgeConflictGuard,
    ContradictionSignalGuard,
    enforce_guard_pipeline,
)


async def enforce_store_guards(
    *,
    content: str,
    project: str,
    tenant_id: str,
    fact_type: str,
    meta: dict[str, Any] | None,
    nemesis_rejection: str | None = None,
    bridge_result: dict[str, Any] | None = None,
) -> None:
    context = {
        "content": content,
        "project": project,
        "tenant_id": tenant_id,
        "fact_type": fact_type,
        "meta": meta or {},
        "nemesis_rejection": nemesis_rejection,
        "bridge_result": bridge_result or {},
    }

    guards = [
        ContradictionSignalGuard(),
        BridgeConflictGuard(),
    ]

    enforce_guard_pipeline(guards, context)
