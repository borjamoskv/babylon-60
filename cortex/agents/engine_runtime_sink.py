"""Runtime sink that persists agent artifacts via the sovereign engine write-path."""

from __future__ import annotations

import hashlib
from typing import Any

from cortex.agents.contracts import (
    CausalEdgePayload,
    DecisionEdgePayload,
    FactProposal,
    RejectionEnvelope,
    ToolEvidencePayload,
)
from cortex.extensions.interfaces.engine import EngineProtocol
from cortex.utils.canonical import canonical_json

__all__ = ["EngineRuntimeSink"]


class EngineRuntimeSink:
    """Persist runtime artifacts through ``engine.store()`` without bypassing guards."""

    def __init__(self, engine: EngineProtocol) -> None:
        self._engine = engine

    async def persist_fact_proposal(self, proposal: FactProposal[dict]) -> None:
        artifact = proposal.model_dump(mode="json")
        await self._engine.store(
            project=proposal.fact.project,
            tenant_id=proposal.fact.tenant_id,
            content=self._proposal_content(proposal),
            fact_type="idea",
            tags=self._tags("proposal", proposal.fact.fact_type, proposal.fact.status),
            confidence="inferred",
            source=f"agent:{proposal.fact.agent_id}",
            meta=self._artifact_meta(
                artifact_kind="fact_proposal",
                schema_name=type(proposal).__name__,
                tenant_id=proposal.fact.tenant_id,
                project=proposal.fact.project,
                unique_key=proposal.proposal_id,
                artifact=artifact,
                runtime_original_fact_type=proposal.fact.fact_type,
                runtime_payload_hash=proposal.fact.payload_hash,
                runtime_status=proposal.fact.status,
                taint=proposal.fact.taint,
            ),
        )

    async def persist_tool_evidence(self, evidence: ToolEvidencePayload) -> None:
        artifact = evidence.model_dump(mode="json")
        await self._engine.store(
            project=evidence.project,
            tenant_id=evidence.tenant_id,
            content=self._tool_evidence_content(evidence),
            fact_type="knowledge",
            tags=self._tags("tool-evidence", evidence.tool_name, evidence.status),
            confidence="verified",
            source=f"tool:{evidence.tool_name}",
            meta=self._artifact_meta(
                artifact_kind="tool_evidence",
                schema_name=type(evidence).__name__,
                tenant_id=evidence.tenant_id,
                project=evidence.project,
                unique_key=evidence.call_id,
                artifact=artifact,
                runtime_tool_name=evidence.tool_name,
                runtime_status=evidence.status,
                runtime_input_hash=evidence.input_hash,
                runtime_output_hash=evidence.output_hash,
                runtime_artifact_ref=evidence.artifact_ref,
                taint=evidence.taint,
            ),
        )

    async def persist_decision_edge(self, edge: DecisionEdgePayload) -> None:
        artifact = edge.model_dump(mode="json")
        await self._engine.store(
            project=edge.project,
            tenant_id=edge.tenant_id,
            content=self._decision_edge_content(edge),
            fact_type="decision",
            tags=self._tags("decision-edge", edge.edge_type),
            confidence="verified",
            source="agent:runtime-sink",
            meta=self._artifact_meta(
                artifact_kind="decision_edge",
                schema_name=type(edge).__name__,
                tenant_id=edge.tenant_id,
                project=edge.project,
                unique_key=edge.edge_id,
                artifact=artifact,
                decision_type="lineage_edge",
                runtime_edge_type=edge.edge_type,
                taint=edge.taint,
            ),
        )

    async def persist_causal_edge(self, edge: CausalEdgePayload) -> None:
        artifact = edge.model_dump(mode="json")
        await self._engine.store(
            project=edge.project,
            tenant_id=edge.tenant_id,
            content=self._causal_edge_content(edge),
            fact_type="knowledge",
            tags=self._tags("causal-edge", edge.edge_type),
            confidence="verified",
            source="agent:runtime-sink",
            meta=self._artifact_meta(
                artifact_kind="causal_edge",
                schema_name=type(edge).__name__,
                tenant_id=edge.tenant_id,
                project=edge.project,
                unique_key=edge.edge_id,
                artifact=artifact,
                runtime_edge_type=edge.edge_type,
                taint=edge.taint,
            ),
        )

    async def persist_rejection(self, rejection: RejectionEnvelope) -> None:
        artifact = rejection.model_dump(mode="json")
        tenant_id = rejection.tenant_id or "default"
        project = rejection.project or "default"
        source = f"agent:{rejection.agent_id}" if rejection.agent_id else "agent:runtime-sink"
        unique_key = (
            rejection.proposal_id or rejection.fact_id or rejection.correlation_id or rejection.code
        )
        await self._engine.store(
            project=project,
            tenant_id=tenant_id,
            content=self._rejection_content(rejection),
            fact_type="decision",
            tags=self._tags("rejection", rejection.failed_stage, rejection.code),
            confidence="verified",
            source=source,
            meta=self._artifact_meta(
                artifact_kind="rejection",
                schema_name=type(rejection).__name__,
                tenant_id=tenant_id,
                project=project,
                unique_key=unique_key,
                artifact=artifact,
                decision_type="rejection",
                runtime_failed_stage=rejection.failed_stage,
                runtime_retryable=rejection.retryable,
                taint=rejection.taint,
            ),
        )

    def _artifact_meta(
        self,
        *,
        artifact_kind: str,
        schema_name: str,
        tenant_id: str,
        project: str,
        unique_key: str,
        artifact: dict[str, Any],
        **extra: Any,
    ) -> dict[str, Any]:
        canonical_artifact = canonical_json(self._artifact_without_taint(artifact))
        return {
            "runtime_artifact_kind": artifact_kind,
            "runtime_schema": schema_name,
            "runtime_artifact_hash": hashlib.sha3_256(
                canonical_artifact.encode("utf-8")
            ).hexdigest(),
            "runtime_idempotency_key": self._idempotency_key(
                tenant_id=tenant_id,
                project=project,
                artifact_kind=artifact_kind,
                unique_key=unique_key,
                canonical_artifact=canonical_artifact,
            ),
            "runtime_artifact": artifact,
            **extra,
        }

    def _artifact_without_taint(self, artifact: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in artifact.items() if key != "taint"}

    def _idempotency_key(
        self,
        *,
        tenant_id: str,
        project: str,
        artifact_kind: str,
        unique_key: str,
        canonical_artifact: str,
    ) -> str:
        payload = "\x00".join([tenant_id, project, artifact_kind, unique_key, canonical_artifact])
        return hashlib.sha3_256(payload.encode("utf-8")).hexdigest()

    def _proposal_content(self, proposal: FactProposal[dict]) -> str:
        return (
            f"[AGENT PROPOSAL] {proposal.fact.fact_type} proposal {proposal.proposal_id} "
            f"from {proposal.fact.agent_id}"
        )

    def _tool_evidence_content(self, evidence: ToolEvidencePayload) -> str:
        return (
            f"[TOOL EVIDENCE] {evidence.tool_name} status={evidence.status} call={evidence.call_id}"
        )

    def _decision_edge_content(self, edge: DecisionEdgePayload) -> str:
        return (
            f"[DECISION EDGE] decision={edge.decision_id} fact={edge.fact_id} type={edge.edge_type}"
        )

    def _causal_edge_content(self, edge: CausalEdgePayload) -> str:
        anchor = edge.parent_id or edge.signal_id or "unknown"
        return f"[CAUSAL EDGE] fact={edge.fact_id} anchor={anchor} type={edge.edge_type}"

    def _rejection_content(self, rejection: RejectionEnvelope) -> str:
        return f"[RUNTIME REJECTION] {rejection.failed_stage}:{rejection.code} {rejection.reason}"

    def _tags(self, *parts: str) -> list[str]:
        tags: list[str] = []
        for part in ("agent-runtime", "runtime-artifact", *parts):
            cleaned = part.strip()
            if not cleaned or cleaned in tags:
                continue
            tags.append(cleaned[:128])
        return tags[:50]
