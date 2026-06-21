import pytest
import asyncio
import struct
from cortex.extensions.ouroboros_mythos.mcts_planner import MCTSPlanner

@pytest.mark.asyncio
async def test_mcts_planner_real_mode():
    planner = MCTSPlanner()
    diagnosis = {"opportunity": "inference_task"}
    
    plan = await planner.synthesize_plan(diagnosis)
    
    assert "steps" in plan
    # BABYLON-60 compliance: expected_exergy_units is now base-60 scaled integer
    assert plan["expected_exergy_units"] == 18000

@pytest.mark.asyncio
async def test_mcts_planner_dream_mode():
    planner = MCTSPlanner(max_depth=3)
    diagnosis = {"anomaly": "high_latency"}
    
    plan = await planner.run_dream_simulation(diagnosis)
    
    assert "trajectory_hash" in plan
    assert plan["expected_exergy_units"] == 45000
    # Assert structural endianness (Little Endian packed u32)
    assert plan["trajectory_hash"] == struct.pack('<I', 123456789)
