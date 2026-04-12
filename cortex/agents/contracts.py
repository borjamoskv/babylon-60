from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = [
    "ApprovalEvent",
    "CausalEdgePayload",
    "DecisionEdgePayload",
    "DeferredAction",
    "FactCommitReceipt",
    "FactProposal",
    "GuardDecision",
    "ProvenanceRecord",
    "RejectionEnvelope",
    "SovereignFact",
    "TaskErrorPayload",
    "TaskCompletedPayload",
    "TaskFailedPayload",
    "TaskRequestPayload",
    "TaskResultPayload",
    "ToolCallPayload",
    "ToolEvidencePayload",
    "ToolResultPayload",
    "VerificationRequestPayload",
    "VerificationResultPayload",
]

PayloadT = TypeVar("PayloadT")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_cortex_taint(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("taint must not be blank")
    if not value.startswith("taint:"):
        raise ValueError("taint must start with 'taint:'")
    return value


class TaskRequestPayload(BaseModel):
    task_id: str
    objective: str
    input: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ToolCallPayload(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultPayload(BaseModel):
    tool_name: str
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class VerificationRequestPayload(BaseModel):
    subject: Literal["tool_result", "task_result", "plan_step"]
    candidate: dict[str, Any]


class VerificationResultPayload(BaseModel):
    ok: bool
    verdict: Literal["accepted", "rejected", "needs_handoff"]
    reasons: list[str] = Field(default_factory=list)


class TaskCompletedPayload(BaseModel):
    task_id: str
    output: dict[str, Any] = Field(default_factory=dict)


class TaskFailedPayload(BaseModel):
    task_id: str
    error: str
    retryable: bool = False


class TaskResultPayload(BaseModel, Generic[PayloadT]):
    ok: Literal[True] = True
    op: str
    result: PayloadT

    @field_validator("op")
    @classmethod
    def _op_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("op must not be blank")
        return value


class TaskErrorPayload(BaseModel):
    ok: Literal[False] = False
    error: str
    op: str | None = None
    supported: list[str] | None = None

    @field_validator("error")
    @classmethod
    def _error_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("error must not be blank")
        return value

    @field_validator("op")
    @classmethod
    def _optional_op_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("op must not be blank when provided")
        return value


class ProvenanceRecord(BaseModel):
    source: str
    captured_at: datetime = Field(default_factory=_utc_now)
    tool_name: str | None = None
    payload_ref: str | None = None
    artifact_hash: str | None = None
    verification_status: Literal["unverified", "verified", "rejected"] = "unverified"
    inference_rule: str | None = None

    @field_validator("source")
    @classmethod
    def _source_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source must not be blank")
        return value


class DeferredAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str
    description: str
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str | None = None
    requires_approval: bool = False


class SovereignFact(BaseModel, Generic[PayloadT]):
    fact_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    agent_id: str
    session_id: str
    project: str = "default"
    fact_type: str = "knowledge"
    schema_version: str = "1.0"
    payload: PayloadT
    payload_hash: str
    taint: str
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    causation_id: str | None = None
    decision_id: str | None = None
    proposal_id: str | None = None
    status: Literal["proposed", "validated", "committed", "rejected"] = "proposed"
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator(
        "tenant_id",
        "agent_id",
        "session_id",
        "project",
        "fact_type",
        "payload_hash",
        "taint",
    )
    @classmethod
    def _required_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text fields must not be blank")
        return value

    @field_validator("taint")
    @classmethod
    def _taint_must_use_cortex_prefix(cls, value: str) -> str:
        return _validate_cortex_taint(value)


class FactProposal(BaseModel, Generic[PayloadT]):
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    fact: SovereignFact[PayloadT]
    rationale: str | None = None
    side_effects: list[DeferredAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_fact_proposal_id(self) -> FactProposal[PayloadT]:
        if self.fact.proposal_id is None:
            self.fact.proposal_id = self.proposal_id
        elif self.fact.proposal_id != self.proposal_id:
            raise ValueError("fact.proposal_id must match proposal_id")
        return self


class GuardDecision(BaseModel):
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    required_corrections: list[str] = Field(default_factory=list)
    guard_name: str | None = None


class ToolEvidencePayload(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    tool_version: str | None = None
    schema_id: str | None = None
    tenant_id: str
    agent_id: str
    session_id: str
    project: str = "default"
    captured_at: datetime = Field(default_factory=_utc_now)
    input_hash: str
    output_hash: str | None = None
    artifact_ref: str | None = None
    status: Literal["ok", "error", "pending"] = "ok"
    error_code: str | None = None
    provenance: ProvenanceRecord | None = None
    taint: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    normalized_arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_status_shape(self) -> ToolEvidencePayload:
        if self.status == "ok" and not (self.output_hash or self.artifact_ref):
            raise ValueError("ok tool evidence requires output_hash or artifact_ref")
        if self.status == "error" and not self.error_code:
            raise ValueError("error tool evidence requires error_code")
        return self

    @field_validator("taint")
    @classmethod
    def _taint_must_use_cortex_prefix(cls, value: str) -> str:
        return _validate_cortex_taint(value)


class ApprovalEvent(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str
    status: Literal["pending", "approved", "rejected", "expired"]
    actor_id: str | None = None
    origin: str | None = None
    reason: str | None = None
    signature: str | None = None
    artifact_hash: str | None = None
    acted_at: datetime | None = None
    correlation_id: str | None = None

    @model_validator(mode="after")
    def _validate_terminal_approval(self) -> ApprovalEvent:
        if self.status in {"approved", "rejected", "expired"} and self.acted_at is None:
            self.acted_at = _utc_now()
        if self.status == "approved" and not self.artifact_hash:
            raise ValueError("approved events require artifact_hash")
        return self


class FactCommitReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: str(uuid4()))
    fact_id: str
    proposal_id: str | None = None
    ledger_hash: str
    committed_at: datetime = Field(default_factory=_utc_now)
    status: Literal["committed"] = "committed"
    outbox_ids: list[str] = Field(default_factory=list)


class RejectionEnvelope(BaseModel):
    proposal_id: str | None = None
    fact_id: str | None = None
    tenant_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    project: str | None = None
    correlation_id: str | None = None
    taint: str
    code: str = "rejected"
    reason: str
    retryable: bool = False
    failed_stage: Literal[
        "guard",
        "taint",
        "schema",
        "encryption",
        "ledger",
        "persistence",
        "index",
        "approval",
        "policy",
        "runtime",
    ] = "guard"
    reasons: list[str] = Field(default_factory=list)

    @field_validator("reason")
    @classmethod
    def _reason_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value

    @field_validator("taint")
    @classmethod
    def _taint_must_use_cortex_prefix(cls, value: str) -> str:
        return _validate_cortex_taint(value)

    @field_validator("tenant_id", "agent_id", "session_id", "project", "correlation_id")
    @classmethod
    def _optional_text_fields_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("optional text fields must not be blank when provided")
        return value


class CausalEdgePayload(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    fact_id: str
    parent_id: str | None = None
    signal_id: str | None = None
    edge_type: Literal[
        "derived_from", "tainted_by", "triggered_by", "supersedes", "contradicts"
    ] = "derived_from"
    tenant_id: str
    project: str = "default"
    taint: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _requires_parent_or_signal(self) -> CausalEdgePayload:
        if self.parent_id is None and self.signal_id is None:
            raise ValueError("causal edges require parent_id or signal_id")
        return self

    @field_validator("taint")
    @classmethod
    def _taint_must_use_cortex_prefix(cls, value: str) -> str:
        return _validate_cortex_taint(value)


class DecisionEdgePayload(BaseModel):
    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    fact_id: str
    edge_type: Literal["used_as_evidence", "supports", "ruled_out", "contradicts"] = (
        "used_as_evidence"
    )
    tenant_id: str
    project: str = "default"
    taint: str
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("taint")
    @classmethod
    def _taint_must_use_cortex_prefix(cls, value: str) -> str:
        return _validate_cortex_taint(value)
