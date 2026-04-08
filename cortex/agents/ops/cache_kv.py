"""Explicit Ops models and handlers for CacheKV."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cortex.agents.builtins._explicit_ops import ExplicitOpsHandler
from cortex.extensions.swarm.kv_prefix_registry import (
    KVPrefixRegistry,
    PrefixSlot,
)

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


def _required_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


class CacheRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PromptRequest(CacheRequest):
    system_prompt: str
    episodic_context: list[dict[str, Any]] | None = None

    @field_validator("system_prompt")
    @classmethod
    def _validate_system_prompt(cls, value: str) -> str:
        return _required_text(value, "system_prompt")


class RegisterRequest(PromptRequest):
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


class GetRequest(PromptRequest):
    op: Literal["get"]
    mission_id: str
    tenant_id: str

    @field_validator("mission_id", "tenant_id")
    @classmethod
    def _validate_required_text_fields(cls, value: str, info: Any) -> str:
        return _required_text(value, str(info.field_name))


class AffinityRequest(PromptRequest):
    op: Literal["affinity"]


class PrefillAcquireRequest(PromptRequest):
    op: Literal["prefill_acquire"]


class PrefillReleaseRequest(PromptRequest):
    op: Literal["prefill_release"]


class ReportRequest(CacheRequest):
    op: Literal["report"]


class StatusRequest(CacheRequest):
    op: Literal["status"]


class PrefixSlotResponse(BaseModel):
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
    def from_slot(cls, slot: PrefixSlot) -> PrefixSlotResponse:
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


class AffinityResponse(BaseModel):
    providers: list[str]


class PrefillAcquireResponse(BaseModel):
    is_leader: bool


class PrefillReleaseResponse(BaseModel):
    released: bool = True


class CacheReportResponse(BaseModel):
    total_slots: int
    total_hits: int
    tokens_saved: int
    estimated_flops_saved: int


class CacheStatusResponse(CacheReportResponse):
    agent: str
    status: Literal["ok"] = "ok"
    supported_ops: list[str] = Field(default_factory=list)


class CacheKVOps(ExplicitOpsHandler):
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
    ) -> BaseModel | dict[str, Any]:
        if op == "register":
            request = RegisterRequest.model_validate(payload)
            slot = self._registry.register(
                mission_id=request.mission_id,
                tenant_id=request.tenant_id,
                system_prompt=request.system_prompt,
                provider_name=request.provider_name,
                model_name=request.model_name,
                ttl_seconds=request.ttl_seconds,
                episodic_context=request.episodic_context,
            )
            return PrefixSlotResponse.from_slot(slot)

        if op == "get":
            request = GetRequest.model_validate(payload)
            slot = self._registry.get_slot(
                mission_id=request.mission_id,
                tenant_id=request.tenant_id,
                system_prompt=request.system_prompt,
                episodic_context=request.episodic_context,
            )
            return PrefixSlotResponse.from_slot(slot) if slot else {}

        if op == "affinity":
            request = AffinityRequest.model_validate(payload)
            return AffinityResponse(
                providers=self._registry.check_cache_affinity(
                    request.system_prompt,
                    episodic_context=request.episodic_context,
                )
            )

        if op == "prefill_acquire":
            request = PrefillAcquireRequest.model_validate(payload)
            return PrefillAcquireResponse(
                is_leader=await self._registry.wait_or_acquire_prefill(
                    request.system_prompt,
                    episodic_context=request.episodic_context,
                )
            )

        if op == "prefill_release":
            request = PrefillReleaseRequest.model_validate(payload)
            self._registry.release_prefill_lock(
                request.system_prompt,
                episodic_context=request.episodic_context,
            )
            return PrefillReleaseResponse()

        if op == "report":
            ReportRequest.model_validate(payload)
            return CacheReportResponse.model_validate(self._registry.exergy_report())

        if op == "status":
            StatusRequest.model_validate(payload)
            report = CacheReportResponse.model_validate(self._registry.exergy_report()).model_dump()
            return CacheStatusResponse(
                agent=agent_id,
                supported_ops=sorted(self.supported_ops),
                **report,
            )

        raise ValueError(f"unknown op: {op!r}")
