import asyncio
import pytest
from unittest.mock import Mock

from cortex.extensions.swarm.byzantine import ByzantineArbiter


@pytest.mark.asyncio
async def test_byzantine_consensus_updates_reputation_and_emits_signals():
    # Arrange
    mock_bus = Mock()
    arbiter = ByzantineArbiter(tolerance_threshold=0.6, signal_bus=mock_bus)

    # Register modes
    arbiter.register_node("node_a", 1.0)
    arbiter.register_node("node_b", 1.0)
    arbiter.register_node("node_c", 1.0)

    # Act: a \& b agree, c hallucinates
    proposals = {"node_a": {"value": 42}, "node_b": {"value": 42}, "node_c": {"value": 99}}

    winner = await arbiter.execute_consensus(proposals)

    # Assert
    assert winner == {"value": 42}

    # Check reputation
    assert arbiter.nodes["node_a"].reputation == 1.0  # capped at 1.0
    assert arbiter.nodes["node_b"].reputation == 1.0
    assert arbiter.nodes["node_c"].reputation == 0.8  # slashed

    # Check emitted signals
    assert mock_bus.emit.call_count == 3
    emit_calls = [c.args[0] for c in mock_bus.emit.call_args_list]

    # Two rewards, one slash
    assert emit_calls.count("trust:reward") == 2
    assert emit_calls.count("trust:slash") == 1
