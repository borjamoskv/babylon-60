"""CORTEX Agents — runtime public API.

Exposes the core agent runtime classes. Extension-layer prompts and pitch
templates remain in ``cortex.extensions.agents``.
"""

from __future__ import annotations

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus, SqliteMessageBus
from cortex.agents.contracts import (
    ApprovalEvent,
    CausalEdgePayload,
    DecisionEdgePayload,
    DeferredAction,
    FactCommitReceipt,
    FactProposal,
    GuardDecision,
    ProvenanceRecord,
    RejectionEnvelope,
    SovereignFact,
    TaskErrorPayload,
    TaskResultPayload,
    ToolEvidencePayload,
)
from cortex.agents.cortex_middleware import CortexAgentMiddleware
from cortex.agents.engine_runtime_sink import EngineRuntimeSink
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import (
    AgentMessage,
    MessageKind,
    MessageState,
    new_message,
)
from cortex.agents.middleware import AgentMiddleware
from cortex.agents.runtime_sink import InMemoryRuntimeSink, RuntimeSink
from cortex.agents.schema import AgentRole
from cortex.agents.state import AgentState, AgentStatus, WorkingMemory
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import Tool, ToolRegistry

__all__ = [
    # Core runtime
    "BaseAgent",
    "AgentMiddleware",
    "CortexAgentMiddleware",
    "EngineRuntimeSink",
    "InMemoryRuntimeSink",
    "RuntimeSink",
    "Supervisor",
    # Manifest & schema
    "AgentManifest",
    "AgentRole",
    # State
    "AgentState",
    "AgentStatus",
    "WorkingMemory",
    # Messaging
    "AgentMessage",
    "MessageBus",
    "MessageKind",
    "MessageState",
    "SqliteMessageBus",
    "new_message",
    # Contracts
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
    "TaskResultPayload",
    "ToolEvidencePayload",
    # Tools
    "Tool",
    "ToolRegistry",
]
