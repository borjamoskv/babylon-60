"""Runtime sinks for sovereign-ready agent artifacts.

These sinks sit between agent middleware and the eventual CORTEX write-path.
They intentionally stay write-path agnostic for now: collect structured
artifacts first, wire them into guards/ledger later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from cortex.agents.contracts import (
    CausalEdgePayload,
    DecisionEdgePayload,
    FactProposal,
    RejectionEnvelope,
    ToolEvidencePayload,
)

__all__ = ["InMemoryRuntimeSink", "RuntimeSink"]


class RuntimeSink(Protocol):
    async def persist_fact_proposal(self, proposal: FactProposal[dict]) -> None: ...

    async def persist_tool_evidence(self, evidence: ToolEvidencePayload) -> None: ...

    async def persist_decision_edge(self, edge: DecisionEdgePayload) -> None: ...

    async def persist_causal_edge(self, edge: CausalEdgePayload) -> None: ...

    async def persist_rejection(self, rejection: RejectionEnvelope) -> None: ...


@dataclass
class InMemoryRuntimeSink:
    """Simple sink for tests and incremental integration."""

    fact_proposals: list[FactProposal[dict]] = field(default_factory=list)
    tool_evidence: list[ToolEvidencePayload] = field(default_factory=list)
    decision_edges: list[DecisionEdgePayload] = field(default_factory=list)
    causal_edges: list[CausalEdgePayload] = field(default_factory=list)
    rejections: list[RejectionEnvelope] = field(default_factory=list)

    async def persist_fact_proposal(self, proposal: FactProposal[dict]) -> None:
        self.fact_proposals.append(proposal)

    async def persist_tool_evidence(self, evidence: ToolEvidencePayload) -> None:
        self.tool_evidence.append(evidence)

    async def persist_decision_edge(self, edge: DecisionEdgePayload) -> None:
        self.decision_edges.append(edge)

    async def persist_causal_edge(self, edge: CausalEdgePayload) -> None:
        self.causal_edges.append(edge)

    async def persist_rejection(self, rejection: RejectionEnvelope) -> None:
        self.rejections.append(rejection)
