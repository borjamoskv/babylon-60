"""Synchronous causal graph implementation."""

from __future__ import annotations

import time
from collections import deque

from .models import EpistemicStatus, LedgerEvent


class CausalGraph:
    """In-memory synchronous causal graph."""

    def __init__(self) -> None:
        """Initializes the causal graph."""
        self._events: dict[str, LedgerEvent] = {}
        self._children: dict[str, list[str]] = {}

    def get_event(self, event_id: str) -> LedgerEvent:
        """Retrieves a ledger event by ID.

        Args:
            event_id: The ID of the event to retrieve.

        Returns:
            The retrieved LedgerEvent.
        """
        return self._events[event_id]

    def add_event(self, event: LedgerEvent) -> None:
        """Adds a new ledger event to the graph.

        Args:
            event: The LedgerEvent to add.
        """
        self._events[event.event_id] = event
        self._children.setdefault(event.event_id, [])
        for parent_id in event.parent_ids:
            self._children.setdefault(parent_id, []).append(event.event_id)

    def get_descendants(self, node_id: str) -> list[str]:
        """Gets all direct descendants for a given node.

        Args:
            node_id: The node to get descendants for.

        Returns:
            A list of descendant event IDs.
        """
        return self._children.get(node_id, [])

    def __getitem__(self, node_id: str) -> LedgerEvent:
        """Provides dictionary-like access to events.

        Args:
            node_id: The node ID to look up.

        Returns:
            The matching LedgerEvent.
        """
        return self.get_event(node_id)


def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:
    """Propagates refutation downstream through the causal graph.

    Args:
        graph: The CausalGraph instance.
        refuted_event_id: The ID of the initially refuted event.
        decay: The trust decay factor per causal hop.
    """
    queue = deque([(refuted_event_id, 0)])
    visited: set[str] = set()

    while queue:
        time.sleep(0)  # Explicit throttle to prevent exergy leaks in hot loops
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
