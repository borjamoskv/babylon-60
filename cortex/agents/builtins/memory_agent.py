# [C5-REAL] Exergy-Maximized
"""
memory_agent.py - MemoryAgent

Reactive agent that wraps CortexMemoryManager. Responds to TASK_REQUEST
messages, executes store/context operations, and emits TASK_RESULT.

NOTE: CortexMemoryManager requires l1, l2, l3, encoder arguments and is a
heavy dependency - callers must inject a fully constructed instance.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.memory.manager import CortexMemoryManager

logger = logging.getLogger(__name__)

_SUPPORTED_OPS: frozenset[str] = frozenset({"store", "context", "status"})


class MemoryAgent(BaseAgent):
    """Reactive agent - governs read/write access to CortexMemoryManager.

    Callers must inject a fully initialised CortexMemoryManager (it requires
    l1/l2/l3/encoder components that are environment-specific).
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        manager: CortexMemoryManager,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._manager = manager

    # ------------------------------------------------------------------
    # Message handler
    # ------------------------------------------------------------------

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        await self.dispatch_task_message(message, _SUPPORTED_OPS, logger)


    async def tick(self) -> None:
        logger.debug("MemoryAgent tick - idle")

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "store":
            return await self._manager.store(
                content=payload.get("content", ""),
                project_id=payload.get("project_id", "default"),
                fact_type=payload.get("fact_type", "general"),
                metadata=payload.get("metadata"),
                layer=payload.get("layer", "semantic"),
            )
        if op == "context":
            return await self._manager.assemble_context(
                query=payload.get("query"),
                project_id=payload.get("project_id", "default"),
                max_episodes=payload.get("max_episodes", 5),
            )
        if op == "status":
            return {"agent": self.manifest.agent_id, "status": "ok"}
        raise ValueError(f"unknown op: {op!r}")


