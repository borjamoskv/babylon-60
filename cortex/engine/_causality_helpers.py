# [C5-REAL] Exergy-Maximized

import json
import logging
import sqlite3
from collections import deque
from typing import Any
import aiosqlite

from cortex.database.core import connect
from cortex.engine.causality_models import (
    EpistemicStatus,
    LedgerEvent,
    TaintStatus,
)
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger("cortex.engine.causality")


class CausalGraph:
    def __init__(self) -> None:
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        return self._events[event_id]

    def add_event(self, event: LedgerEvent) -> None:
        self._events[event.event_id] = event
        self._children.setdefault(event.event_id, [])
        for parent_id in event.parent_ids:
            self._children.setdefault(parent_id, []).append(event.event_id)

    def get_descendants(self, node_id: str) -> list[str]:
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
    queue = deque([(refuted_event_id, 0)])
    visited: set[str] = set()

    while queue:
        node_id, depth = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        try:
            event = graph[node_id]
        except KeyError:
            continue

        if depth == 0:
            event.status = EpistemicStatus.REFUTED
            event.trust_score = 0.0
        else:
            event.trust_score = max(0.0, event.trust_score * (1.0 - decay / max(depth, 1)))
            event.tainted = True

        for child_id in graph.get_descendants(node_id):
            if child_id not in visited:
                queue.append((child_id, depth + 1))


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
        except (sqlite3.Error, ValueError, RuntimeError) as e:
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
        except (sqlite3.Error, ValueError, RuntimeError) as e:
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


def parse_metadata_helper(
    raw_meta: str, tenant_id: str, enc: Any
) -> tuple[dict[str, Any], bool, bool]:
    """Helper to decrypt and parse metadata JSON."""
    if not raw_meta:
        return {}, False, False

    if isinstance(raw_meta, str) and raw_meta.startswith(enc.PREFIX):
        try:
            meta = enc.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
            return meta, True, True
        except (ValueError, TypeError):
            logger.warning("Failed to decrypt metadata")
            return {}, False, False

    try:
        meta = json.loads(raw_meta)
        return meta, True, False
    except (TypeError, json.JSONDecodeError):
        return {"_raw": raw_meta}, False, False


def derive_node_status_helper(
    curr_id: int,
    source_id: int,
    edges: dict[int, list[int]],
    nodes_data: dict[int, dict[str, Any]],
    node_states: dict[int, TaintStatus],
) -> TaintStatus:
    """Determines the TaintStatus of a node based on its parents."""
    if curr_id == source_id:
        return TaintStatus.TAINTED

    parents = edges.get(curr_id, [])
    if not parents:
        return TaintStatus.CLEAN

    p_states = []
    for pid in parents:
        if pid in node_states:
            p_states.append(node_states[pid])
        else:
            p_meta = nodes_data.get(pid, {}).get("metadata", {})
            p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
            p_states.append(
                TaintStatus(p_status)
                if p_status in TaintStatus._value2member_map_
                else TaintStatus.CLEAN
            )

    if all(s == TaintStatus.TAINTED for s in p_states):
        return TaintStatus.TAINTED
    if any(s in (TaintStatus.TAINTED, TaintStatus.SUSPECT) for s in p_states):
        return TaintStatus.SUSPECT
    return TaintStatus.CLEAN
