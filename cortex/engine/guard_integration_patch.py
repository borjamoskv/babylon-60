"""
Temporary integration module to wire fail-closed guard runtime into the store path
without mutating the original store_validation.py inline.

This module can be imported and called from StoreMixin or the validation layer
as a drop-in enforcement step.
"""

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
    """Fail-closed enforcement hook for the store pipeline.

    Should be called BEFORE final commit/persistence.
    """

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
