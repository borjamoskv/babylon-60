"""Causal graph and taint propagation utilities for CORTEX."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.database.core import connect
from cortex.engine.causality_graphs import AsyncCausalGraph, CausalGraph, propagate_refutation
from cortex.engine.causality_models import (
    CONFIDENCE_LEVELS,
    EDGE_DERIVED_FROM,
    EDGE_TAINTED_BY,
    EDGE_TRIGGERED_BY,
    EDGE_UPDATED_FROM,
    Confidence,
    EpistemicStatus,
    LedgerEvent,
    TaintReport,
    TaintStatus,
    _downgrade_confidence,
)
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")

__all__ = [
    "EDGE_DERIVED_FROM",
    "EDGE_TAINTED_BY",
    "EDGE_TRIGGERED_BY",
    "EDGE_UPDATED_FROM",
    "AsyncCausalGraph",
    "AsyncCausalOracle",
    "CausalGraph",
    "CausalOracle",
    "Confidence",
    "CONFIDENCE_LEVELS",
    "EpistemicStatus",
    "LedgerEvent",
    "TaintReport",
    "TaintStatus",
    "_downgrade_confidence",
    "link_causality",
    "propagate_refutation",
    "rowless_json",
]


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(tenant_id=tenant_id, project=project, limit=5)
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except Exception as e:
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
    def find_parent_signal(
        db_path: str,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        try:
            with connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(tenant_id=tenant_id, project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:
            logger.debug("Sync causal lookup failed: %s", e)
        return None


def link_causality(
    meta: dict[str, Any] | None,
    signal_id: int | None,
) -> dict[str, Any]:
    """Attach causal metadata to a fact's meta dictionary."""
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m


def rowless_json(data: dict[str, Any]) -> str:
    return json.dumps(data)
