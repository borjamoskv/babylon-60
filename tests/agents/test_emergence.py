"""Tests for JIT Autopoiesis & Spontaneous Agent Spawning via Emergence Engine."""

import asyncio
from typing import Any

import pytest

from cortex.agents.base import BaseAgent
from cortex.agents.emergence import EmergenceEngine, ResonanceTrigger
from cortex.agents.manifest import AgentManifest
from cortex.agents.state import AgentState, AgentStatus
from cortex.agents.supervisor import Supervisor
from cortex.events.bus import DistributedEventBus


class DummyEphemeralAgent(BaseAgent):
    """A transient agent synthesized for testing Emergence."""

    def __init__(
        self, agent_id: str, payload_context: dict[str, Any], bus: DistributedEventBus
    ) -> None:
        manifest = AgentManifest(
            agent_id=f"Ephemeral-{agent_id}",
            purpose="Fixes voids",
        )
        super().__init__(manifest=manifest, bus=bus)
        self._agent_id = agent_id
        self.payload_context = payload_context
        self.state = AgentState(status=AgentStatus.IDLE)
        self.did_run = False

    @property
    def agent_id(self) -> str:
        return self._agent_id

    async def start(self) -> asyncio.Task[None]:
        self.state.status = AgentStatus.RUNNING
        return asyncio.create_task(self._dummy_loop())

    async def _dummy_loop(self) -> None:
        self.did_run = True
        await asyncio.sleep(0.1)
        # Finish its task
        self.state.status = AgentStatus.STOPPED

    async def stop(self) -> None:
        self.state.status = AgentStatus.STOPPED

    def force_stop(self) -> None:
        self.state.status = AgentStatus.STOPPED


@pytest.fixture
def event_bus() -> DistributedEventBus:
    return DistributedEventBus()


@pytest.fixture
def supervisor() -> Supervisor:
    return Supervisor()


@pytest.fixture
async def emergence_engine(
    supervisor: Supervisor, event_bus: DistributedEventBus
) -> EmergenceEngine:
    engine = EmergenceEngine(
        supervisor=supervisor, event_bus=event_bus, max_active_ephemeral=3, exergy_budget=10
    )
    await engine.start()
    yield engine
    await engine.stop()


@pytest.mark.asyncio
async def test_emergence_spawns_ephemeral_agent(
    supervisor: Supervisor,
    event_bus: DistributedEventBus,
    emergence_engine: EmergenceEngine,
):
    """Verify that an agency void trigger correctly synthesizes an ephemeral agent."""

    # 1. Define heuristic trigger
    def heuristic_condition(event: dict[str, Any]) -> bool:
        return event.get("type") == "anomaly.detected"

    def factory(context: dict[str, Any]) -> BaseAgent:
        agent_id = f"Ghost-{context.get('hash', '000')}"
        return DummyEphemeralAgent(agent_id, context, bus=event_bus)

    trigger = ResonanceTrigger(
        name="AnomalyFixer",
        condition=heuristic_condition,
        agent_factory=factory,
        exergy_cost=2,
    )
    emergence_engine.add_trigger(trigger)

    assert supervisor.agent_count == 0
    assert emergence_engine.remaining_exergy == 10

    # 2. Fire the resonance event
    await event_bus.publish("system.anomaly", {"type": "anomaly.detected", "hash": "A1B2"})

    # Wait for the async propagation
    await asyncio.sleep(0.05)

    # 3. Assert emergence
    assert supervisor.agent_count == 1
    assert "Ghost-A1B2" in supervisor._agents
    entry = supervisor._agents["Ghost-A1B2"]

    assert entry.ephemeral is True
    assert entry.agent.state.status == AgentStatus.RUNNING
    assert emergence_engine.remaining_exergy == 8  # Subtracted config cost

    # Allow agent to run its dummy task and finish
    await asyncio.sleep(0.2)

    # 4. Verify auto-cleanup on health_check
    await supervisor.health_check()
    assert supervisor.agent_count == 0  # Ephemeral agent should be cleaned up


@pytest.mark.asyncio
async def test_emergence_respects_exergy_budget(
    supervisor: Supervisor,
    event_bus: DistributedEventBus,
    emergence_engine: EmergenceEngine,
):
    """Verify that agents are not spawned if budget is exceeded."""

    trigger = ResonanceTrigger(
        name="ExpensiveAgent",
        condition=lambda e: True,
        agent_factory=lambda ctx: DummyEphemeralAgent("Exp", ctx, bus=event_bus),
        exergy_cost=20,  # budget is only 10
    )
    emergence_engine.add_trigger(trigger)

    await event_bus.publish("some.event", {"hello": "world"})
    await asyncio.sleep(0.05)

    assert supervisor.agent_count == 0


@pytest.mark.asyncio
async def test_emergence_prevents_cascades(
    supervisor: Supervisor,
    event_bus: DistributedEventBus,
    emergence_engine: EmergenceEngine,
):
    """Verify that ephemeral agents' own triggers don't cause infinite loops using taint checking."""

    trigger = ResonanceTrigger(
        name="GenericSpawny",
        condition=lambda e: True,  # Matches everything
        agent_factory=lambda ctx: DummyEphemeralAgent(
            f"Spawn-{ctx.get('_topic')}", ctx, bus=event_bus
        ),
        exergy_cost=1,
    )
    emergence_engine.add_trigger(trigger)

    # 1. Fire normal event - Should spawn
    await event_bus.publish("user.action", {})
    await asyncio.sleep(0.05)
    assert emergence_engine.remaining_exergy == 9
    assert supervisor.agent_count == 1

    # 2. Fire tainted event - Should NOT spawn
    await event_bus.publish("system.internal", {"cortex_taint_ephemeral": True})
    await asyncio.sleep(0.05)

    # Exergy should still be 9, meaning no agent was spawned
    assert emergence_engine.remaining_exergy == 9
    # Agent count remains 1 from the first step
    assert supervisor.agent_count == 1
