from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

import pytest

from cortex.agents.base import BaseAgent
from cortex.agents.cortex_middleware import CortexAgentMiddleware
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.middleware import AgentMiddleware
from cortex.agents.runtime_sink import InMemoryRuntimeSink
from cortex.agents.state import AgentStatus
from cortex.agents.tools import ToolRegistry
from cortex.events.bus import DistributedEventBus


class QueueBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = defaultdict(asyncio.Queue)
        self.sent: list[AgentMessage] = []

    async def send(self, message: AgentMessage) -> None:
        self.sent.append(message)
        await self._queues[message.recipient].put(message)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        try:
            return await asyncio.wait_for(self._queues[agent_id].get(), timeout)
        except asyncio.TimeoutError:
            return None


class DummyTool:
    def __init__(self, name: str = "dummy", result: str = "ok") -> None:
        self._name = name
        self._result = result

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, **kwargs: Any) -> Any:
        return {"result": self._result, "kwargs": kwargs}


class RecordingMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        self.before: list[tuple[str, str | None]] = []
        self.after: list[tuple[str, str | None, str | None]] = []
        self.tool_calls: list[tuple[str, dict[str, Any]]] = []
        self.tool_results: list[tuple[str, str | None]] = []
        self.handoffs: list[tuple[str, dict[str, Any]]] = []
        self.retries: list[tuple[str, str | None, int]] = []

    async def before_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
    ) -> None:
        self.before.append((step_kind, message.kind.value if message else None))

    async def after_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
        error: str | None = None,
    ) -> None:
        self.after.append((step_kind, message.kind.value if message else None, error))

    async def on_tool_call(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        self.tool_calls.append((tool_name, arguments))

    async def on_tool_result(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any = None,
        error: str | None = None,
    ) -> None:
        self.tool_results.append((tool_name, error))

    async def on_handoff(
        self,
        agent: BaseAgent,
        *,
        recipient: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> None:
        self.handoffs.append((recipient, payload))

    async def on_retry(
        self,
        agent: BaseAgent,
        *,
        error: str,
        message: AgentMessage | None = None,
        consecutive_errors: int,
    ) -> None:
        self.retries.append((error, message.kind.value if message else None, consecutive_errors))


class RecordingAgent(BaseAgent):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.handled: list[str] = []

    async def handle_message(self, message: AgentMessage) -> None:
        self.handled.append(message.kind.value)


class ToolUsingAgent(BaseAgent):
    async def handle_message(self, message: AgentMessage) -> None:
        await self.use_tool("dummy", payload=message.payload)


class FailingAgent(BaseAgent):
    async def handle_message(self, message: AgentMessage) -> None:
        raise RuntimeError("boom")


def _manifest(agent_id: str, *, max_errors: int = 3, tools_allowed: list[str] | None = None):
    return AgentManifest(
        agent_id=agent_id,
        purpose="test",
        max_consecutive_errors=max_errors,
        tools_allowed=tools_allowed or [],
    )


@pytest.mark.asyncio
async def test_middleware_records_before_and_after_message_steps() -> None:
    bus = QueueBus()
    middleware = RecordingMiddleware()
    agent = RecordingAgent(_manifest("agent-1"), bus, middlewares=[middleware])

    await bus.send(new_message("tester", "agent-1", MessageKind.TASK_REQUEST, {"x": 1}))
    await bus.send(new_message("tester", "agent-1", MessageKind.SHUTDOWN, {}))

    await agent.run()

    assert middleware.before == [("message", "task.request")]
    assert middleware.after == [("message", "task.request", None)]


@pytest.mark.asyncio
async def test_middleware_records_tool_calls_and_results() -> None:
    bus = QueueBus()
    middleware = RecordingMiddleware()
    registry = ToolRegistry()
    registry.register(DummyTool())
    agent = ToolUsingAgent(
        _manifest("agent-2", tools_allowed=["dummy"]),
        bus,
        tool_registry=registry,
        middlewares=[middleware],
    )

    result = await agent.use_tool("dummy", payload={"x": 1})

    assert result["result"] == "ok"
    assert middleware.tool_calls == [("dummy", {"payload": {"x": 1}})]
    assert middleware.tool_results == [("dummy", None)]


@pytest.mark.asyncio
async def test_request_handoff_uses_shared_hook_surface() -> None:
    bus = QueueBus()
    middleware = RecordingMiddleware()
    agent = RecordingAgent(_manifest("agent-3"), bus, middlewares=[middleware])

    await agent.request_handoff(
        "handoff-agent",
        {"task_id": "t-1", "reason": "needs_review"},
        correlation_id="corr-1",
        causation_id="msg-1",
    )

    sent = bus.sent[-1]
    assert sent.kind == MessageKind.HANDOFF_REQUEST
    assert sent.recipient == "handoff-agent"
    assert middleware.handoffs == [
        ("handoff-agent", {"task_id": "t-1", "reason": "needs_review"})
    ]


@pytest.mark.asyncio
async def test_retry_hook_runs_on_runtime_error() -> None:
    bus = QueueBus()
    middleware = RecordingMiddleware()
    agent = FailingAgent(
        _manifest("agent-4", max_errors=1),
        bus,
        middlewares=[middleware],
    )

    await bus.send(new_message("tester", "agent-4", MessageKind.TASK_REQUEST, {"x": 1}))

    await agent.run()

    assert agent.state.status == AgentStatus.QUARANTINED
    assert len(middleware.retries) == 1
    assert middleware.retries[0][1] == "task.request"
    assert middleware.after[0][2] is not None


@pytest.mark.asyncio
async def test_cortex_agent_middleware_records_tool_evidence_and_events() -> None:
    bus = QueueBus()
    event_bus = DistributedEventBus()
    seen: list[dict[str, Any]] = []

    async def _capture(payload: dict[str, Any]) -> None:
        seen.append(payload)

    event_bus.subscribe("agents.runtime.tool.result", _capture)

    registry = ToolRegistry()
    registry.register(DummyTool())
    middleware = CortexAgentMiddleware(event_bus=event_bus)
    agent = ToolUsingAgent(
        _manifest("agent-5", tools_allowed=["dummy"]),
        bus,
        tool_registry=registry,
        middlewares=[middleware],
    )
    agent.state.metadata["session_id"] = "sess-5"
    agent.state.metadata["project"] = "proj-5"

    result = await agent.use_tool("dummy", payload={"x": 1})

    runtime_bucket = agent.memory.scratchpad["_cortex_runtime"]
    evidence = runtime_bucket["tool_evidence"][0]

    assert result["result"] == "ok"
    assert evidence.tool_name == "dummy"
    assert evidence.session_id == "sess-5"
    assert evidence.project == "proj-5"
    assert evidence.status == "ok"
    assert len(seen) == 1
    assert seen[0]["tool_name"] == "dummy"


@pytest.mark.asyncio
async def test_cortex_agent_middleware_populates_runtime_sink() -> None:
    bus = QueueBus()
    sink = InMemoryRuntimeSink()
    registry = ToolRegistry()
    registry.register(DummyTool())
    middleware = CortexAgentMiddleware(sink=sink)
    agent = ToolUsingAgent(
        _manifest("agent-6", tools_allowed=["dummy"]),
        bus,
        tool_registry=registry,
        middlewares=[middleware],
    )
    agent.state.metadata["session_id"] = "sess-6"
    agent.state.metadata["project"] = "proj-6"

    await bus.send(new_message("tester", "agent-6", MessageKind.TASK_REQUEST, {"x": 1}))
    await bus.send(new_message("tester", "agent-6", MessageKind.SHUTDOWN, {}))

    await agent.run()

    assert len(sink.fact_proposals) == 1
    assert sink.fact_proposals[0].fact.fact_type == "agent_step"
    assert sink.fact_proposals[0].fact.session_id == "sess-6"
    assert sink.fact_proposals[0].fact.taint.startswith("taint:")
    assert len(sink.tool_evidence) == 1
    assert sink.tool_evidence[0].tool_name == "dummy"
    assert sink.tool_evidence[0].taint.startswith("taint:")


@pytest.mark.asyncio
async def test_cortex_agent_middleware_persists_runtime_rejection_on_retry() -> None:
    bus = QueueBus()
    sink = InMemoryRuntimeSink()
    middleware = CortexAgentMiddleware(sink=sink)
    agent = FailingAgent(
        _manifest("agent-7", max_errors=1),
        bus,
        middlewares=[middleware],
    )

    await bus.send(new_message("tester", "agent-7", MessageKind.TASK_REQUEST, {"x": 1}))

    await agent.run()

    assert agent.state.status == AgentStatus.QUARANTINED
    assert len(sink.rejections) == 1
    assert sink.rejections[0].failed_stage == "runtime"
    assert sink.rejections[0].retryable is True
    assert sink.rejections[0].taint.startswith("taint:")
