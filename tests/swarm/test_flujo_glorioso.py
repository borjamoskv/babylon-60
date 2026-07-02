import pytest
import json
from unittest.mock import AsyncMock
from babylon60.swarm.flujo_glorioso import DecaCoreOrchestrator
from babylon60.engine.causal.belief_objects import BeliefObject
from babylon60.database.belief_store import BeliefStore

@pytest.fixture
def mock_store():
    store = AsyncMock(spec=BeliefStore)
    store.insert_belief = AsyncMock(return_value=1)
    return store

@pytest.mark.asyncio
async def test_flujo_glorioso_concepcion(mock_store):
    orchestrator = DecaCoreOrchestrator(mock_store)
    input_data = {"idea": "glorious concept"}
    result = await orchestrator.concepcion(input_data)
    
    assert isinstance(result, BeliefObject)
    assert result.payload.context_hash == "concepcion_ctx"
    
    output_data = json.loads(result.payload.content)
    assert output_data["idea"] == "glorious concept"
    assert output_data["concepcion_completed"] is True
    assert output_data["agent_role"] == "Musa"
    mock_store.insert_belief.assert_awaited_once()

@pytest.mark.asyncio
async def test_flujo_glorioso_full_pipeline(mock_store):
    orchestrator = DecaCoreOrchestrator(mock_store)
    trajectory = await orchestrator.execute_genesis("omega project")
    
    assert len(trajectory) == 10
    
    # Assert causality: The final state must have accumulated completions
    final_belief = trajectory[-1]
    final_data = json.loads(final_belief.payload.content)
    
    assert final_data["idea"] == "omega project"
    assert final_data["concepcion_completed"] is True
    assert final_data["despliegue_completed"] is True
    assert final_data["agent_role"] == "Comandante"
    
    assert mock_store.insert_belief.call_count == 10
