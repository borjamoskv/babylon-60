"""CacheKVAgent with typed ops and stable response envelopes."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cortex.agents.builtins._explicit_ops import ExplicitOpsAgent, ExplicitOpsHandler
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.tools import ToolRegistry
from cortex.extensions.swarm.kv_prefix_registry import (
    KVPrefixRegistry,
    PrefixSlot,
    get_kv_registry,
)

logger = logging.getLogger(__name__)

_SUPPORTED_OPS: frozenset[str] = frozenset(
    {
        "register",
        "get",
        "affinity",
        "prefill_acquire",
        "prefill_release",
        "report",
        "status",
    }
)


class _CacheRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _PromptRequest(_CacheRequest):
    system_prompt: str
    episodic_context: list[dict[str, Any]] | None = None

    @field_validator("system_prompt")
    @classmethod
    def _validate_system_prompt(cls, value: str) -> str:
        return _required_text(value, "system_prompt")


class _RegisterRequest(_PromptRequest):
    op: Literal["register"]
    mission_id: str
    tenant_id: str
    provider_name: str
    model_name: str
    ttl_seconds: int = 3600

    @field_validator("mission_id", "tenant_id", "provider_name", "model_name")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info: Any) -> str:
        return _required_text(value, str(info.field_name))


class _GetRequest(_PromptRequest):
    op: Literal["get"]
    mission_id: str
    tenant_id: str

    @field_validator("mission_id", "tenant_id")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info: Any) -> str:
        return _required_text(value, str(info.field_name))


class _AffinityRequest(_PromptRequest):
    op: Literal["affinity"]


class _PrefillAcquireRequest(_PromptRequest):
    op: Literal["prefill_acquire"]


class _PrefillReleaseRequest(_PromptRequest):
    op: Literal["prefill_release"]


class _ReportRequest(_CacheRequest):
    op: Literal["report"]


class _StatusRequest(_CacheRequest):
    op: Literal["status"]


class _PrefixSlotResponse(BaseModel):
    cache_key: str
    mission_id: str
    tenant_id: str
    prefix_hash: str
    prefix_tokens: int
    provider_name: str
    model_name: str
    ttl_seconds: int
    created_at: str
    expires_at: float
    hits: int

    @classmethod
    def from_slot(cls, slot: PrefixSlot) -> _PrefixSlotResponse:
        return cls(
            cache_key=slot.cache_key,
            mission_id=slot.mission_id,
            tenant_id=slot.tenant_id,
            prefix_hash=slot.prefix_hash,
            prefix_tokens=slot.prefix_tokens,
            provider_name=slot.provider_name,
            model_name=slot.model_name,
            ttl_seconds=slot.ttl_seconds,
            created_at=slot.created_at,
            expires_at=slot.expires_at,
            hits=slot.hits,
        )


class _AffinityResponse(BaseModel):
    providers: list[str]


class _PrefillAcquireResponse(BaseModel):
    is_leader: bool


class _PrefillReleaseResponse(BaseModel):
    released: bool = True


class _CacheReportResponse(BaseModel):
    total_slots: int
    total_hits: int
    tokens_saved: int
    estimated_flops_saved: int


class _CacheStatusResponse(_CacheReportResponse):
    agent: str
    status: Literal["ok"] = "ok"
    supported_ops: list[str] = Field(default_factory=list)


class _CacheKVOps(ExplicitOpsHandler):
    supported_ops: frozenset[str] = _SUPPORTED_OPS

    def __init__(self, registry: KVPrefixRegistry) -> None:
        self._registry = registry

    def normalize_op(self, op: str) -> str:
        return op

    async def execute(
        self,
        op: str,
        payload: dict[str, Any],
        *,
        agent_id: str,
    ) -> Any:
        if op == "register":
            request = _RegisterRequest.model_validate(payload)
            slot = self._registry.register(
                mission_id=request.mission_id,
                tenant_id=request.tenant_id,
                system_prompt=request.system_prompt,
                provider_name=request.provider_name,
                model_name=request.model_name,
                ttl_seconds=request.ttl_seconds,
                episodic_context=request.episodic_context,
            )
            return _PrefixSlotResponse.from_slot(slot).model_dump()

        if op == "get":
            request = _GetRequest.model_validate(payload)
            slot = self._registry.get_slot(
                mission_id=request.mission_id,
                tenant_id=request.tenant_id,
                system_prompt=request.system_prompt,
                episodic_context=request.episodic_context,
            )
            return None if slot is None else _PrefixSlotResponse.from_slot(slot).model_dump()

        if op == "affinity":
            request = _AffinityRequest.model_validate(payload)
            response = _AffinityResponse(
                providers=self._registry.check_cache_affinity(
                    request.system_prompt,
                    episodic_context=request.episodic_context,
                )
            )
            return response.model_dump()

        if op == "prefill_acquire":
            request = _PrefillAcquireRequest.model_validate(payload)
            response = _PrefillAcquireResponse(
                is_leader=await self._registry.wait_or_acquire_prefill(
                    request.system_prompt,
                    episodic_context=request.episodic_context,
                )
            )
            return response.model_dump()

        if op == "prefill_release":
            request = _PrefillReleaseRequest.model_validate(payload)
            self._registry.release_prefill_lock(
                request.system_prompt,
                episodic_context=request.episodic_context,
            )
            return _PrefillReleaseResponse().model_dump()

        if op == "report":
            _ReportRequest.model_validate(payload)
            return _CacheReportResponse.model_validate(self._registry.exergy_report()).model_dump()

        if op == "status":
            _StatusRequest.model_validate(payload)
            report = _CacheReportResponse.model_validate(
                self._registry.exergy_report()
            ).model_dump()
            return _CacheStatusResponse(
                agent=agent_id,
                supported_ops=sorted(self.supported_ops),
                **report,
            ).model_dump()

        raise ValueError(f"unknown op: {op!r}")


class CacheKVAgent(ExplicitOpsAgent):
    """Reactive agent for tenant-safe KV prefix cache management."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        registry: KVPrefixRegistry | None = None,
    ) -> None:
        super().__init__(
            manifest,
            bus,
            tool_registry,
            ops_handler=_CacheKVOps(registry or get_kv_registry()),
        )

    async def tick(self) -> None:
        logger.debug("CacheKVAgent tick - idle")


def _required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text
