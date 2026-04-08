"""
memento_agent.py — MementoAgent

Reactive memory agent focused on explicit remember/recall semantics.
Wraps CortexMemoryManager and exposes a narrow, user-facing vocabulary
while preserving compatibility aliases for store/context.
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

_SUPPORTED_OPS: frozenset[str] = frozenset({"remember", "recall", "status", "store", "context"})
_OP_ALIASES: dict[str, str] = {
    "store": "remember",
    "context": "recall",
}


class MementoAgent(BaseAgent):
    """Reactive agent — explicit remember/recall facade over CortexMemoryManager."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        manager: CortexMemoryManager,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._manager = manager

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        raw_op = str(payload.get("op", ""))
        op = _OP_ALIASES.get(raw_op, raw_op)

        if op not in {"remember", "recall", "status"}:
            await self._reply(
                message,
                {"error": f"unsupported op: {raw_op!r}", "supported": sorted(_SUPPORTED_OPS)},
            )
            return

        try:
            result = await self._dispatch(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("MementoAgent op=%s failed", op)
            await self._reply(message, {"op": op, "error": str(exc)})

    async def tick(self) -> None:
        logger.debug("MementoAgent tick — idle")

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "remember":
            return await self._manager.store(
                tenant_id=payload.get("tenant_id"),
                project_id=payload.get("project_id", "default"),
                content=payload.get("content", ""),
                fact_type=payload.get("fact_type", "general"),
                metadata=payload.get("metadata"),
                layer=payload.get("layer", "semantic"),
                parent_decision_id=payload.get("parent_decision_id"),
                use_bus=bool(payload.get("use_bus", False)),
            )

        if op == "recall":
            return await self._manager.assemble_context(
                tenant_id=payload.get("tenant_id"),
                query=payload.get("query"),
                project_id=payload.get("project_id", "default"),
                max_episodes=int(payload.get("max_episodes", 5)),
            )

        if op == "status":
            return {
                "agent": self.manifest.agent_id,
                "status": "ok",
                "supported_ops": sorted(_SUPPORTED_OPS),
            }

        raise ValueError(f"unknown op: {op!r}")

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
