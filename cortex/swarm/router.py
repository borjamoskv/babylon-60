from __future__ import annotations

import copy

from cortex.swarm.ledger.engine import SwarmLedger
from cortex.swarm.ledger.models import SwarmEvent
from cortex.swarm.graph_source import GraphSource, SalienceCandidate


class SwarmRouter:
    """
    Routes requests using either:
      1. SNGraphSource  — SN subgraph drives candidate selection (neural mode)
      2. registry       — classic registry fallback

    In both cases every decision is appended to SwarmLedger.
    _dispatch() is a pure function: no side effects, no self state reads.
    """

    def __init__(self, registry, graph_source: GraphSource | None = None):
        self.registry = registry
        self.graph_source = graph_source
        self.ledger = SwarmLedger()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, request: dict) -> dict:
        if self.graph_source is not None:
            raw_candidates = self.graph_source.get_candidates(request["task"])
            candidates = [c.to_dict() for c in raw_candidates]
            registry_snapshot = self._frozen_snapshot()
        else:
            if not self.registry._frozen:
                self.registry.freeze()
            raw_candidates = sorted(
                self.registry.get_candidates(request["task"]),
                key=lambda a: a.agent_id,
            )
            candidates = [getattr(a, '__dict__', {"agent_id": a.agent_id}) for a in raw_candidates]
            registry_snapshot = self._frozen_snapshot()

        selected = _dispatch(candidates, request)

        # Serialize capabilities to sorted list for JSON stability
        for k, v in selected.items():
            if isinstance(v, (set, frozenset)):
                selected[k] = sorted(list(v))

        # Generate stable routing_hash
        import hashlib, json
        state_str = json.dumps(selected, sort_keys=True)
        routing_hash = hashlib.sha256(state_str.encode()).hexdigest()
        selected["routing_hash"] = routing_hash

        selected_agent = selected.get("agent_id", "unknown")

        self.ledger.append(
            SwarmEvent(
                task=request["task"],
                input=copy.deepcopy(request),
                registry_state=registry_snapshot,
                selected_agent=selected["agent_id"],
                routing_payload=selected,
            )
        )

        return selected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _frozen_snapshot(self) -> dict:
        """Deep-frozen, sorted snapshot of registry state."""
        raw = (
            self.registry.snapshot()
            if hasattr(self.registry, 'snapshot')
            else {}
        )
        return _deep_sorted(copy.deepcopy(raw))


# ------------------------------------------------------------------
# Pure functions  (no self, no side-effects)
# ------------------------------------------------------------------

def _dispatch(candidates: list[dict], request: dict) -> dict:
    """Pure selection: first candidate after deterministic sort."""
    if not candidates:
        raise ValueError(f"No candidates for task: {request['task']}")
    return candidates[0]


def _deep_sorted(obj):
    """Recursively sort dict keys for deterministic hashing."""
    if isinstance(obj, dict):
        return {k: _deep_sorted(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_sorted(i) for i in obj]
    return obj
