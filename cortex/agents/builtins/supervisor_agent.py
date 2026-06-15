# [C5-REAL] Exergy-Maximized
"""
supervisor_agent.py - SupervisorAgent

Reactive agent that wraps the Supervisor to provide a message-based control
plane for agent lifecycle operations: start, stop, quarantine, status.
External callers can request lifecycle operations via TASK_REQUEST messages
instead of calling the Supervisor directly.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

_OPS: frozenset[str] = frozenset({"start", "stop", "quarantine", "status", "health"})


class SupervisorAgent(BaseAgent):
    """Reactive agent - exposes Supervisor lifecycle ops over the message bus."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        supervisor: Supervisor,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._supervisor = supervisor

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        await self.dispatch_task_message(message, _OPS, logger)

    async def tick(self) -> None:
        """Periodic health-check tick - detects stale agents."""
        await self._supervisor.health_check()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        agent_id: str = payload.get("agent_id", "")

        if op == "start":
            if not agent_id:
                raise ValueError("agent_id required for start")
            await self._supervisor.start_agent(agent_id)
            return {"started": agent_id}

        if op == "stop":
            if not agent_id:
                raise ValueError("agent_id required for stop")
            await self._supervisor.stop_agent(agent_id)
            return {"stopped": agent_id}

        if op == "quarantine":
            if not agent_id:
                raise ValueError("agent_id required for quarantine")
            await self._supervisor.quarantine_agent(agent_id)
            return {"quarantined": agent_id}

        if op == "status":
            return self._supervisor.status()

        if op == "health":
            await self._supervisor.health_check()
            return self._supervisor.status()

        raise ValueError(f"unhandled op: {op!r}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
