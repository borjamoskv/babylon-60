# [C5-REAL] Exergy-Maximized
"""
End-to-End Swarm Integration Tests for CORTEX-Persist

Validates:
1. Concurrency and isolation of SqliteMessageBus
2. Supervisor fault tolerance under aggressive load
3. Causal Scheduler (TopologicalArbitrage) integration with MessageBus
"""

import asyncio
import logging
import uuid
from typing import Any

import pytest

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message, AgentMessage
from cortex.agents.state import AgentStatus
from cortex.agents.supervisor import Supervisor
from cortex.database.pool import CortexConnectionPool
from cortex.engine.causal.topological_arbitrage import TopologyIndex
from cortex.database.schema import get_all_schema

logger = logging.getLogger(__name__)


def _unique_db() -> str:
    """Return a unique in-memory SQLite URI per call."""
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


async def setup_db_for_topology(db_path: str):
    """Setup schema for topological arbitrage."""
    pool = CortexConnectionPool(db_path, read_only=False)
    await pool.initialize()
    async with pool.acquire() as conn:
        for sql in get_all_schema():
            if "USING vec0" in sql:
                continue
            try:
                await conn.executescript(sql)
            except Exception as e:
                pass
        await conn.commit()
    await pool.close()
    return CortexConnectionPool(db_path, read_only=False)


class PingPongAgent(BaseAgent):
    """Agent that replies to ping messages and tracks counts."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pings_received = 0
        self.pongs_sent = 0
        
    async def handle_message(self, message: AgentMessage) -> None:
        if message.kind == MessageKind.TASK_REQUEST and message.payload.get("action") == "ping":
            self.pings_received += 1
            await self.send_result(
                message.sender,
                {"action": "pong", "count": self.pings_received},
                correlation_id=message.correlation_id
            )
            self.pongs_sent += 1


class ChaosAgent(BaseAgent):
    """Agent that randomly crashes to test Supervisor fault tolerance."""
    
    def __init__(self, *args, crash_on_tick: int = 3, **kwargs):
        super().__init__(*args, **kwargs)
        self.tick_count = 0
        self.crash_on_tick = crash_on_tick
        
    async def tick(self) -> None:
        self.tick_count += 1
        if self.tick_count >= self.crash_on_tick:
            raise RuntimeError("Induced chaos crash")


def _make_manifest(agent_id: str) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="E2E test agent",
        tools_allowed=[],
        daemon=True,
        max_consecutive_errors=2,
    )


@pytest.mark.asyncio
async def test_e2e_concurrent_message_bus_routing():
    """Test 10 agents sending and receiving hundreds of messages simultaneously."""
    db_path = _unique_db()
    bus = SqliteMessageBus(db_path=db_path)
    supervisor = Supervisor(heartbeat_timeout_s=5.0)
    
    NUM_AGENTS = 10
    MESSAGES_PER_AGENT = 20
    
    agents = []
    for i in range(NUM_AGENTS):
        agent_id = f"agent_{i}"
        manifest = _make_manifest(agent_id)
        agent = PingPongAgent(manifest=manifest, bus=bus)
        agents.append(agent)
        supervisor.register(agent)
        await supervisor.start_agent(agent_id)
        
    # Send messages concurrently
    send_tasks = []
    for sender in agents:
        for recipient in agents:
            if sender.agent_id != recipient.agent_id:
                for _ in range(MESSAGES_PER_AGENT):
                    msg = new_message(
                        sender=sender.agent_id,
                        recipient=recipient.agent_id,
                        kind=MessageKind.TASK_REQUEST,
                        payload={"action": "ping"}
                    )
                    send_tasks.append(bus.send(msg))
                    
    await asyncio.gather(*send_tasks)
    
    # Wait for processing
    await asyncio.sleep(2.0)
    
    # Assertions
    total_pings = 0
    total_pongs = 0
    for agent in agents:
        total_pings += agent.pings_received
        total_pongs += agent.pongs_sent
        
    expected_messages = NUM_AGENTS * (NUM_AGENTS - 1) * MESSAGES_PER_AGENT
    assert total_pings == expected_messages
    assert total_pongs == expected_messages
    
    for agent in agents:
        assert await bus.pending_count(agent.agent_id) == 0
        await supervisor.stop_agent(agent.agent_id)

    await bus.close()


@pytest.mark.asyncio
async def test_e2e_supervisor_fault_tolerance_under_load():
    """Test that supervisor accurately isolates failing agents while healthy agents continue."""
    db_path = _unique_db()
    bus = SqliteMessageBus(db_path=db_path)
    supervisor = Supervisor(heartbeat_timeout_s=2.0)
    
    # Healthy agents
    healthy_agents = []
    for i in range(3):
        agent = PingPongAgent(manifest=_make_manifest(f"healthy_{i}"), bus=bus)
        healthy_agents.append(agent)
        supervisor.register(agent)
        await supervisor.start_agent(agent.agent_id)
        
    # Chaos agents
    chaos_agents = []
    for i in range(3):
        agent = ChaosAgent(manifest=_make_manifest(f"chaos_{i}"), bus=bus, crash_on_tick=2)
        chaos_agents.append(agent)
        supervisor.register(agent)
        await supervisor.start_agent(agent.agent_id)
        
    # Let ticks run
    await asyncio.sleep(1.0)
    
    # Verify states
    for agent in healthy_agents:
        assert agent.state.status in (AgentStatus.RUNNING, AgentStatus.IDLE)
        
    for agent in chaos_agents:
        # After crashing twice (max_consecutive_errors=2), they should be QUARANTINED
        assert agent.state.status == AgentStatus.QUARANTINED
        
    for agent in healthy_agents:
        await supervisor.stop_agent(agent.agent_id)
        
    await bus.close()


@pytest.mark.asyncio
async def test_e2e_causal_scheduler_and_bus_integration():
    """Test integration between SqliteMessageBus and TopologyIndex under shared connection pool."""
    db_path = _unique_db()
    
    # We must ensure both components can coexist using causal_write correctly.
    pool = await setup_db_for_topology(db_path)
    
    # Topology Index connects via pool
    async with pool.acquire() as conn:
        topology = TopologyIndex(conn)
        # Should execute safely without lock/auth errors
        await topology.sync()
        
    # Message Bus
    bus = SqliteMessageBus(db_path=db_path)
    agent = PingPongAgent(manifest=_make_manifest("topo_agent"), bus=bus)
    
    # Send some messages
    await bus.send(new_message("sys", "topo_agent", MessageKind.TASK_REQUEST, {"action": "ping"}))
    await asyncio.sleep(0.1) # Agent processes message
    
    assert await bus.pending_count("topo_agent") == 1 # Unconsumed until tick, we didn't start the agent
    
    # Retrieve explicitly
    msg = await bus.receive("topo_agent")
    assert msg is not None
    assert msg.payload.get("action") == "ping"
    
    await bus.close()
    await pool.close()
