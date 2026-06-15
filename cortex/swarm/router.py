"""
cortex/swarm/router.py - SwarmRouter V2: deterministic pure-function routing.

Design invariants for deterministic replay:
- route() is a pure function: same input + same registry state = same output
- NO global mutable state modified during route()
- NO time.time(), random, uuid4() or LLM calls inside route()
- capability scoring uses integer arithmetic only (no floats)
- agent resolution uses sorted() for stable tie-breaking
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from cortex.swarm.registry import AgentRegistry, AgentSpec


class RouterError(Exception):
    """Raised when routing cannot be resolved."""


# ---------------------------------------------------------------------------
# Capability keyword index
# Maps task keywords -> capability strings
# Deterministic: dict literal, never mutated at runtime
# ---------------------------------------------------------------------------
_CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    "analyze": ["analyze", "audit"],
    "audit": ["audit", "analyze"],
    "read": ["read"],
    "write": ["write"],
    "compute": ["compute", "transform"],
    "transform": ["transform", "compute"],
    "memory": ["read", "write"],
    "ledger": ["audit", "analyze"],
    "anomal": ["audit", "analyze"],
    "consist": ["audit", "read"],
}


def _extract_capabilities(task: str) -> list[str]:
    """
    Extract required capabilities from task string.

    Pure function: only string ops, no I/O.
    Result is sorted for stable output.
    """
    task_lower = task.lower()
    matched: set[str] = set()

    for keyword, caps in _CAPABILITY_KEYWORDS.items():
        if keyword in task_lower:
            matched.update(caps)

    return sorted(matched)  # sorted for determinism


def _score_agent(agent: AgentSpec, required_caps: list[str]) -> int:
    """
    Integer score: number of required capabilities the agent covers.

    Integer arithmetic only — no floats to avoid quantization drift.
    """
    return sum(1 for cap in required_caps if cap in agent.capabilities)


def _select_agents(
    registry: AgentRegistry,
    required_caps: list[str],
) -> list[str]:
    """
    Select agents to handle the task.

    Selection algorithm (deterministic):
    1. Score each agent by integer capability match
    2. Sort by (score DESC, agent_id ASC) for stable tie-breaking
    3. Take all agents with score > 0; fallback to all sorted agents

    Returns list of agent_ids (strings) for JSON serializability.
    """
    all_agents = registry.all()  # already sorted by agent_id

    scored = [
        (agent.agent_id, _score_agent(agent, required_caps))
        for agent in all_agents
    ]

    # Sort: score DESC, agent_id ASC (stable tie-break)
    scored_sorted = sorted(scored, key=lambda x: (-x[1], x[0]))

    # Filter to agents with score > 0
    selected = [agent_id for agent_id, score in scored_sorted if score > 0]

    # Fallback: if no capability match, return all agents sorted by id
    if not selected:
        selected = [agent.agent_id for agent in all_agents]

    return selected


class SwarmRouter:
    """
    SwarmRouter V2: deterministic routing of tasks to agents.

    route() is designed as a pure function:
    - reads registry (immutable during routing)
    - no global state mutation
    - no randomness or time dependency
    - output is fully JSON-serializable
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def route(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Route a request to the best matching agents.

        Args:
            request: dict with 'task' (str) and 'context' (dict)

        Returns:
            Deterministic routing decision:
            {
                "task": str,
                "required_capabilities": list[str],
                "selected_agents": list[str],
                "routing_hash": str,  # SHA256 of stable input
                "registry_snapshot": dict,
            }

        Invariants:
            - same request + same registry => byte-identical output
            - routing_hash is deterministic (no uuid, no time)
        """
        task = request.get("task", "")
        context = request.get("context", {})

        # 1. Extract capabilities (pure, deterministic)
        required_caps = _extract_capabilities(task)

        # 2. Select agents (deterministic: sorted scoring)
        selected_agents = _select_agents(self._registry, required_caps)

        # 3. Registry snapshot (stable serialization)
        registry_snapshot = self._registry.to_dict()

        # 4. Routing hash: SHA256 of stable input
        # Uses sort_keys=True and separators for canonical JSON
        hash_input = json.dumps(
            {
                "task": task,
                "context": context,
                "required_capabilities": required_caps,
                "selected_agents": selected_agents,
                "registry_snapshot": registry_snapshot,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        routing_hash = hashlib.sha256(hash_input).hexdigest()

        return {
            "task": task,
            "required_capabilities": required_caps,
            "selected_agents": selected_agents,
            "routing_hash": routing_hash,
            "registry_snapshot": registry_snapshot,
        }

    def registry_checksum(self) -> str:
        """
        Stable SHA256 of current registry state.

        Useful for golden fixture versioning:
        hash(input + registry_checksum) => versioned routing vector.
        """
        payload = json.dumps(
            self._registry.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
