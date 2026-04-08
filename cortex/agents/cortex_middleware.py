"""CORTEX-shaped runtime middleware for agents.

This layer builds structured runtime artifacts from agent hooks without
writing directly to the sovereign write-path. It is intentionally
ephemeral-first: useful now for runtime observability and ready to be
wired into ledger/guards later.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from cortex.agents.contracts import (
    FactProposal,
    ProvenanceRecord,
    RejectionEnvelope,
    SovereignFact,
    ToolEvidencePayload,
)
from cortex.agents.middleware import AgentMiddleware
from cortex.agents.runtime_sink import RuntimeSink
from cortex.guards.taint import TaintEngine

if TYPE_CHECKING:
    from cortex.agents.base import BaseAgent
    from cortex.agents.message_schema import AgentMessage
    from cortex.events.bus import DistributedEventBus

__all__ = ["CortexAgentMiddleware"]


class CortexAgentMiddleware(AgentMiddleware):
    """Collect structured runtime evidence for later sovereign persistence."""

    def __init__(
        self,
        *,
        event_bus: DistributedEventBus | None = None,
        sink: RuntimeSink | None = None,
        topic_prefix: str = "agents.runtime",
    ) -> None:
        self._event_bus = event_bus
        self._sink = sink
        self._topic_prefix = topic_prefix

    async def before_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
    ) -> None:
        event = {
            "event": "before_step",
            "agent_id": agent.agent_id,
            "tenant_id": agent.manifest.tenant_id,
            "session_id": self._session_id(agent, message),
            "step_kind": step_kind,
            "message_kind": message.kind.value if message else None,
            "correlation_id": message.correlation_id if message else None,
        }
        self._remember(agent, "steps", event)
        await self._publish("step.before", event)

    async def after_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
        error: str | None = None,
    ) -> None:
        event = {
            "event": "after_step",
            "agent_id": agent.agent_id,
            "tenant_id": agent.manifest.tenant_id,
            "session_id": self._session_id(agent, message),
            "step_kind": step_kind,
            "message_kind": message.kind.value if message else None,
            "correlation_id": message.correlation_id if message else None,
            "error": error,
        }
        self._remember(agent, "steps", event)
        if step_kind == "message":
            proposal = self._build_fact_proposal(
                agent,
                fact_type="agent_step",
                payload=event,
                correlation_id=message.correlation_id if message else None,
                causation_id=message.message_id if message else None,
            )
            self._remember(agent, "fact_proposals", proposal)
            await self._persist_fact_proposal(proposal)
        await self._publish("step.after", event)

    async def on_tool_call(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        pending = {
            "tool_name": tool_name,
            "arguments": arguments,
            "input_hash": self._hash_payload(arguments),
        }
        bucket = self._bucket(agent)
        bucket.setdefault("pending_tool_calls", []).append(pending)
        await self._publish(
            "tool.call",
            {
                "agent_id": agent.agent_id,
                "tenant_id": agent.manifest.tenant_id,
                "session_id": self._session_id(agent),
                **pending,
            },
        )

    async def on_tool_result(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any = None,
        error: str | None = None,
    ) -> None:
        pending = self._pop_pending_tool_call(agent, tool_name, arguments)
        input_hash = pending["input_hash"] if pending else self._hash_payload(arguments)
        session_id = self._session_id(agent)
        evidence = ToolEvidencePayload(
            tool_name=tool_name,
            tenant_id=agent.manifest.tenant_id,
            agent_id=agent.agent_id,
            session_id=session_id,
            project=self._project(agent),
            input_hash=input_hash,
            output_hash=self._hash_payload(result) if error is None else None,
            status="error" if error else "ok",
            error_code="tool_execution_failed" if error else None,
            provenance=ProvenanceRecord(
                source=f"agent:{agent.agent_id}",
                tool_name=tool_name,
                payload_ref=f"runtime://tool/{tool_name}",
                verification_status="unverified",
            ),
            arguments=arguments,
            normalized_arguments=arguments,
            taint=self._taint_from_digest(agent.agent_id, session_id, input_hash),
        )
        self._remember(agent, "tool_evidence", evidence)
        await self._persist_tool_evidence(evidence)
        await self._publish("tool.result", evidence.model_dump(mode="json"))

    async def on_handoff(
        self,
        agent: BaseAgent,
        *,
        recipient: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> None:
        event = {
            "agent_id": agent.agent_id,
            "tenant_id": agent.manifest.tenant_id,
            "session_id": self._session_id(agent),
            "recipient": recipient,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "payload_hash": self._hash_payload(payload),
            "payload": payload,
        }
        self._remember(agent, "handoffs", event)
        proposal = self._build_fact_proposal(
            agent,
            fact_type="handoff_request",
            payload=event,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        self._remember(agent, "fact_proposals", proposal)
        await self._persist_fact_proposal(proposal)
        await self._publish("handoff", event)

    async def on_retry(
        self,
        agent: BaseAgent,
        *,
        error: str,
        message: AgentMessage | None = None,
        consecutive_errors: int,
    ) -> None:
        event = {
            "agent_id": agent.agent_id,
            "tenant_id": agent.manifest.tenant_id,
            "session_id": self._session_id(agent, message),
            "message_kind": message.kind.value if message else None,
            "correlation_id": message.correlation_id if message else None,
            "error": error,
            "consecutive_errors": consecutive_errors,
        }
        rejection_payload = {
            "proposal_id": None,
            "fact_id": None,
            "tenant_id": agent.manifest.tenant_id,
            "agent_id": agent.agent_id,
            "session_id": self._session_id(agent, message),
            "project": self._project(agent),
            "correlation_id": message.correlation_id if message else None,
            "code": "runtime_retry",
            "reason": error,
            "retryable": True,
            "failed_stage": "runtime",
            "reasons": [error],
        }
        rejection_hash = self._hash_payload(rejection_payload)
        self._remember(agent, "retries", event)
        rejection = RejectionEnvelope(
            tenant_id=agent.manifest.tenant_id,
            agent_id=agent.agent_id,
            session_id=self._session_id(agent, message),
            project=self._project(agent),
            correlation_id=message.correlation_id if message else None,
            taint=self._taint_from_digest(
                agent.agent_id,
                self._session_id(agent, message),
                rejection_hash,
            ),
            code="runtime_retry",
            reason=error,
            retryable=True,
            failed_stage="runtime",
            reasons=[error],
        )
        self._remember(agent, "rejections", rejection)
        await self._persist_rejection(rejection)
        await self._publish("retry", event)

    def _bucket(self, agent: BaseAgent) -> dict[str, Any]:
        return agent.memory.scratchpad.setdefault("_cortex_runtime", {})

    def _remember(self, agent: BaseAgent, key: str, value: Any) -> None:
        bucket = self._bucket(agent)
        bucket.setdefault(key, []).append(value)

    def _pop_pending_tool_call(
        self,
        agent: BaseAgent,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        bucket = self._bucket(agent)
        pending_calls: list[dict[str, Any]] = bucket.setdefault("pending_tool_calls", [])
        for index in range(len(pending_calls) - 1, -1, -1):
            candidate = pending_calls[index]
            if candidate["tool_name"] == tool_name and candidate["arguments"] == arguments:
                return pending_calls.pop(index)
        return None

    def _session_id(self, agent: BaseAgent, message: AgentMessage | None = None) -> str:
        session_id = agent.state.metadata.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            return session_id
        if message is not None and message.correlation_id:
            return message.correlation_id
        return f"runtime:{agent.agent_id}"

    def _project(self, agent: BaseAgent) -> str:
        project = agent.state.metadata.get("project")
        if isinstance(project, str) and project.strip():
            return project
        return "default"

    def _hash_payload(self, payload: Any) -> str:
        canonical = self._canonical_payload(payload)
        return hashlib.sha3_256(canonical.encode("utf-8")).hexdigest()

    def _taint_from_digest(self, agent_id: str, session_id: str, digest: str) -> str:
        return f"taint:{agent_id}:{session_id}:{self._utc_now_iso()}:{digest}"

    def _utc_now_iso(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def _canonical_payload(self, payload: Any) -> str:
        return json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

    def _build_fact_proposal(
        self,
        agent: BaseAgent,
        *,
        fact_type: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None,
    ) -> FactProposal[dict]:
        canonical_payload = self._canonical_payload(payload)
        payload_hash = hashlib.sha3_256(canonical_payload.encode("utf-8")).hexdigest()
        session_id = self._session_id(agent)
        fact = SovereignFact[dict](
            tenant_id=agent.manifest.tenant_id,
            agent_id=agent.agent_id,
            session_id=session_id,
            project=self._project(agent),
            fact_type=fact_type,
            payload=payload,
            payload_hash=payload_hash,
            taint=TaintEngine.generate_taint(agent.agent_id, session_id, canonical_payload),
            provenance=[
                ProvenanceRecord(
                    source=f"agent:{agent.agent_id}",
                    payload_ref=f"runtime://{fact_type}",
                    artifact_hash=payload_hash,
                    verification_status="unverified",
                )
            ],
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        return FactProposal[dict](fact=fact)

    async def _persist_fact_proposal(self, proposal: FactProposal[dict]) -> None:
        if self._sink is None:
            return
        await self._sink.persist_fact_proposal(proposal)

    async def _persist_tool_evidence(self, evidence: ToolEvidencePayload) -> None:
        if self._sink is None:
            return
        await self._sink.persist_tool_evidence(evidence)

    async def _persist_rejection(self, rejection: RejectionEnvelope) -> None:
        if self._sink is None:
            return
        await self._sink.persist_rejection(rejection)

    async def _publish(self, suffix: str, payload: dict[str, Any]) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(f"{self._topic_prefix}.{suffix}", payload)
