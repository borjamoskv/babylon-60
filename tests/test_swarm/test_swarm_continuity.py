import pytest
from unittest.mock import AsyncMock, Mock

from cortex.verification.swarm_continuity import SwarmContinuityVerifier


@pytest.mark.asyncio
async def test_swarm_continuity_verifier_stores_facts():
    # Arrange
    mock_bus = AsyncMock()
    mock_fact_manager = AsyncMock()

    verifier = SwarmContinuityVerifier(mock_bus, mock_fact_manager)

    # Mocking signals returned by the bus
    mock_dead_signal = Mock()
    mock_dead_signal.event_type = "node:dead"
    mock_dead_signal.id = 1
    mock_dead_signal.project = "TEST_PROJECT"
    mock_dead_signal.payload = {"node_id": "test_node", "new_status": "DEAD", "elapsed_s": 120.5}

    mock_reward_signal = Mock()
    mock_reward_signal.event_type = "trust:reward"
    mock_reward_signal.id = 2
    mock_reward_signal.project = "TEST_PROJECT"
    mock_reward_signal.payload = {
        "node_id": "good_node",
        "new_reputation": 1.05,
        "reason": "Proposed winning hash",
    }

    # poll returns the dead signal on first call ("node:dead"),
    # empty on suspect/trust:slash, and reward on the 4th call
    async def side_effect_poll(event_type, consumer, limit):
        if event_type == "node:dead":
            return [mock_dead_signal]
        elif event_type == "trust:reward":
            return [mock_reward_signal]
        return []

    mock_bus.poll.side_effect = side_effect_poll

    # Act
    processed = await verifier.poll_and_verify(limit=10)

    # Assert
    assert processed == 2
    assert mock_fact_manager.store.call_count == 2

    # Verify the exact parameters of the first store call (the node:dead one)
    call_args_1 = mock_fact_manager.store.call_args_list[0].kwargs
    assert call_args_1["fact_type"] == "swarm_event"
    assert call_args_1["confidence"] == "C5-Verified"
    assert "DEAD after 120.5s" in call_args_1["content"]
    assert call_args_1["meta"]["signal_id"] == 1

    # Verify the exact parameters of the second store call (the trust:reward one)
    call_args_2 = mock_fact_manager.store.call_args_list[1].kwargs
    assert call_args_2["fact_type"] == "trust_score"
    assert call_args_2["confidence"] == "C5-Consensus"
    assert "rewarded. New reputation: 1.05" in call_args_2["content"]
    assert call_args_2["meta"]["signal_id"] == 2
