"""Unit tests for LEGION-OMEGA — cortex/engine/legion.py."""

import asyncio
import pytest
from cortex.engine.legion import (
    AsyncSignalBus, SwarmSignal, BlueTeamAgent, RedTeamSwarm,
    LegionOmegaEngine, SwarmAgent
)

@pytest.mark.asyncio
async def test_async_signal_bus_void_invariant():
    """Test VOID invariant: Drop empty signals immediately."""
    bus = AsyncSignalBus()

    # Valid signal
    sig1 = SwarmSignal(agent_id="A1", target="T1", status="SUCCESS", payload={"data": 1}, metrics={})
    await bus.emit(sig1)

    # Empty payload signal (should be marked VOID)
    sig2 = SwarmSignal(agent_id="A2", target="T2", status="SUCCESS", payload={}, metrics={})
    await bus.emit(sig2)

    signals = await bus.get_all()
    assert len(signals) == 2
    assert signals[0].status == "SUCCESS"
    assert signals[1].status == "VOID"

@pytest.mark.asyncio
async def test_blue_team_epigenetic_synthesis():
    """Test Blue Team synthesis with epigenetic rules."""
    blue = BlueTeamAgent()

    # Initial synthesis without feedback
    code1 = await blue.synthesize("sleep and eval", context={})
    assert "Intent: sleep and eval" in code1

    # Synthesis with feedback triggering epigenetic rules
    # "eval" feedback should trigger ast.literal_eval
    # "sleep" feedback should trigger asyncio.sleep
    feedback = ["Contains eval", "Uses time.sleep"]
    code2 = await blue.synthesize("secure worker", context={}, feedback=feedback)

    assert "import ast" in code2
    assert "ast.literal_eval" in code2
    assert "import asyncio" in code2
    assert "await asyncio.sleep(1)" in code2

class MockAttackVector:
    def __init__(self, name="mock_vector"):
        self.name = name
    async def attack(self, code, context):
        if "eval" in code:
            return ["Insecure eval detected"]
        return []

@pytest.mark.asyncio
async def test_red_team_siege():
    """Test Red Team siege with mocked attack vectors."""
    mock_vector = MockAttackVector(name="mock_eval")
    red = RedTeamSwarm(vectors=[mock_vector], replica_count=2)

    # Code with vulnerability
    vulnerabilities = await red.siege("eval(cmd)", context={})
    # RedTeamSwarm.siege flattens findings from all agents
    # total_agents = len(vectors) * replica_count = 1 * 2 = 2
    assert len(vulnerabilities) == 2
    assert vulnerabilities[0] == "Insecure eval detected"

    # Secure code
    vulnerabilities2 = await red.siege("print('hello')", context={})
    assert len(vulnerabilities2) == 0

@pytest.mark.asyncio
async def test_legion_omega_forge_stability():
    """Test LegionOmegaEngine forge cycle and Thermal Stagnation Guard."""
    mock_vector = MockAttackVector(name="mock_eval")
    engine = LegionOmegaEngine(max_cycles=3, vectors=[mock_vector])

    # Successful forge (already secure)
    result = await engine.forge("secure_op")
    assert result.success is True
    # Initial synthesis -> Siege (0 vulnerabilities) -> Success
    assert result.cycles == 1

    # Forge with persistent vulnerabilities to test stagnation/max cycles
    class PersistentAttack:
        name = "persistent"
        async def attack(self, code, context):
            return ["Persistent bug"]

    engine2 = LegionOmegaEngine(max_cycles=2, vectors=[PersistentAttack()])
    result3 = await engine2.forge("fail_me")
    assert result3.success is False
    # If it reached max_cycles=2, cycles should be 2
    assert result3.cycles <= 2

@pytest.mark.asyncio
async def test_swarm_agent_error_handling():
    """Test SwarmAgent error handling during run."""
    class ErrorAgent(SwarmAgent):
        async def execute(self, target):
            raise ValueError("Execution failed")

    bus = AsyncSignalBus()
    agent = ErrorAgent(agent_id="Err1", bus=bus)
    queue = asyncio.Queue()
    queue.put_nowait("target1")

    await agent.run(queue)

    signals = await bus.get_all()
    assert len(signals) == 1
    assert signals[0].status == "FAILURE"
    assert "Execution failed" in signals[0].payload["error"]
