"""Shared explicit-op helpers for manager-backed builtin agents."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

_HANDLED_AGENT_ERRORS = (KeyError, OSError, RuntimeError, TypeError, ValueError)


class ExplicitOpRequest(BaseModel):
    """Validated TASK_REQUEST payload for op-driven builtin agents."""

    model_config = ConfigDict(extra="allow")

    op: str

    @field_validator("op")
    @classmethod
    def _op_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("op must not be blank")
        return value


class ExplicitOpsHandler(Protocol):
    """Adapter contract for manager-backed builtin agents."""

    supported_ops: frozenset[str]

    def normalize_op(self, op: str) -> str: ...

    async def execute(
        self,
        op: str,
        payload: dict[str, Any],
        *,
        agent_id: str,
    ) -> Any: ...


class MemoryManagerLike(Protocol):
    async def store(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        content: str = "",
        fact_type: str = "general",
        metadata: dict[str, Any] | None = None,
        layer: str = "semantic",
        parent_decision_id: str | int | None = None,
        use_bus: bool = False,
    ) -> str: ...

    async def assemble_context(
        self,
        tenant_id: str | None = None,
        project_id: str = "default",
        query: str | None = None,
        max_episodes: int = 3,
        fuse_context: bool = False,
        layer: str | None = None,
    ) -> dict[str, Any]: ...


class SupervisorLike(Protocol):
    async def start_agent(self, agent_id: str) -> None: ...
    async def stop_agent(self, agent_id: str) -> None: ...
    async def quarantine_agent(self, agent_id: str) -> None: ...
    async def health_check(self) -> dict[str, Any] | None: ...
    def status(self) -> dict[str, Any]: ...


class ExplicitOpsAgent(BaseAgent):
    """Base agent that routes TASK_REQUEST payloads through explicit ops."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        ops_handler: ExplicitOpsHandler,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._ops_handler = ops_handler

    @property
    def supported_ops(self) -> frozenset[str]:
        return self._ops_handler.supported_ops

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        raw_op = payload.get("op")
        try:
            request = ExplicitOpRequest.model_validate(payload)
        except ValidationError as exc:
            await self.send_task_error(
                message.sender,
                str(exc),
                op=str(raw_op).strip() if raw_op is not None else None,
                supported=sorted(self.supported_ops),
                correlation_id=message.message_id,
            )
            return

        op = self._ops_handler.normalize_op(request.op)
        normalized_payload = dict(payload)
        normalized_payload["op"] = op

        if op not in self.supported_ops:
            await self.send_task_error(
                message.sender,
                f"unsupported op: {request.op!r}",
                op=request.op,
                supported=sorted(self.supported_ops),
                correlation_id=message.message_id,
            )
            return

        try:
            result = await self._ops_handler.execute(
                op,
                normalized_payload,
                agent_id=self.manifest.agent_id,
            )
        except _HANDLED_AGENT_ERRORS as exc:
            logger.exception("%s op=%s failed", self.__class__.__name__, op)
            await self.send_task_error(
                message.sender,
                str(exc),
                op=op,
                supported=sorted(self.supported_ops),
                correlation_id=message.message_id,
            )
            return

        await self.send_task_result(
            message.sender,
            op,
            result,
            correlation_id=message.message_id,
        )


class MemoryManagerOps:
    """Explicit op adapter for CortexMemoryManager."""

    supported_ops: frozenset[str] = frozenset({"store", "context", "status"})

    def __init__(self, manager: MemoryManagerLike) -> None:
        self._manager = manager

    def normalize_op(self, op: str) -> str:
        return op

    async def execute(
        self,
        op: str,
        payload: dict[str, Any],
        *,
        agent_id: str,
    ) -> dict[str, Any]:
        if op == "store":
            tenant_id = _required_str(payload, "tenant_id")
            project_id = str(payload.get("project_id", "default"))
            fact_type = str(payload.get("fact_type", "general"))
            layer = str(payload.get("layer", "semantic"))
            fact_id = await self._manager.store(
                tenant_id=tenant_id,
                content=str(payload.get("content", "")),
                project_id=project_id,
                fact_type=fact_type,
                metadata=_optional_dict(payload.get("metadata"), key="metadata"),
                layer=layer,
            )
            return {
                "agent": agent_id,
                "manager": type(self._manager).__name__,
                "fact_id": fact_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "fact_type": fact_type,
                "layer": layer,
            }

        if op == "context":
            tenant_id = _required_str(payload, "tenant_id")
            project_id = str(payload.get("project_id", "default"))
            query = _optional_str(payload.get("query"))
            max_episodes = int(payload.get("max_episodes", 5))
            context = await self._manager.assemble_context(
                tenant_id=tenant_id,
                query=query,
                project_id=project_id,
                max_episodes=max_episodes,
                layer=_optional_str(payload.get("layer")),
            )
            return {
                "agent": agent_id,
                "manager": type(self._manager).__name__,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "query": query,
                "max_episodes": max_episodes,
                "context": context,
            }

        if op == "status":
            return {
                "agent": agent_id,
                "status": "ok",
                "manager": type(self._manager).__name__,
                "supported_ops": sorted(self.supported_ops),
            }

        raise ValueError(f"unknown op: {op!r}")


class SupervisorManagerOps:
    """Explicit op adapter for Supervisor lifecycle operations."""

    supported_ops: frozenset[str] = frozenset({"start", "stop", "quarantine", "status", "health"})

    def __init__(self, supervisor: SupervisorLike) -> None:
        self._supervisor = supervisor

    def normalize_op(self, op: str) -> str:
        return op

    async def health_check(self) -> None:
        await self._supervisor.health_check()

    async def execute(
        self,
        op: str,
        payload: dict[str, Any],
        *,
        agent_id: str,
    ) -> dict[str, Any]:
        if op == "start":
            target_agent_id = _required_str(payload, "agent_id")
            await self._supervisor.start_agent(target_agent_id)
            return {
                "agent": agent_id,
                "manager": type(self._supervisor).__name__,
                "started": target_agent_id,
            }

        if op == "stop":
            target_agent_id = _required_str(payload, "agent_id")
            await self._supervisor.stop_agent(target_agent_id)
            return {
                "agent": agent_id,
                "manager": type(self._supervisor).__name__,
                "stopped": target_agent_id,
            }

        if op == "quarantine":
            target_agent_id = _required_str(payload, "agent_id")
            await self._supervisor.quarantine_agent(target_agent_id)
            return {
                "agent": agent_id,
                "manager": type(self._supervisor).__name__,
                "quarantined": target_agent_id,
            }

        if op == "status":
            return {
                "agent": agent_id,
                "status": "ok",
                "manager": type(self._supervisor).__name__,
                "supported_ops": sorted(self.supported_ops),
                "agents": self._supervisor.status(),
            }

        if op == "health":
            await self._supervisor.health_check()
            return {
                "agent": agent_id,
                "status": "ok",
                "manager": type(self._supervisor).__name__,
                "supported_ops": sorted(self.supported_ops),
                "agents": self._supervisor.status(),
            }

        raise ValueError(f"unknown op: {op!r}")


def coerce_memory_manager_ops(manager: MemoryManagerLike | MemoryManagerOps) -> MemoryManagerOps:
    if isinstance(manager, MemoryManagerOps):
        return manager
    return MemoryManagerOps(manager)


def coerce_supervisor_ops(
    supervisor: Supervisor | SupervisorLike | SupervisorManagerOps,
) -> SupervisorManagerOps:
    if isinstance(supervisor, SupervisorManagerOps):
        return supervisor
    return SupervisorManagerOps(supervisor)


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"{key} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{key} is required")
    return text


def _optional_dict(value: Any, *, key: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
