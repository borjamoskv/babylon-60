import asyncio
import json
import pytest
from cortex.engine.isolation import SimpleIsolationEngine
from cortex.agents.arc_agi_3.agent import ARCAgent
from cortex.agents.arc_agi_3.reasoning import PeARLProgram

@pytest.mark.asyncio
async def test_isolation_manager_success():
    engine = SimpleIsolationEngine()
    code = "import json\nprint(json.dumps({'output': [[1, 2], [3, 4]]}))"
    result = await engine.execute_sandbox(code)
    assert result is not None
    # Assuming code outputs to stdout
    out_dict = json.loads(result.stdout)
    assert out_dict['output'] == [[1, 2], [3, 4]]

@pytest.mark.asyncio
async def test_isolation_manager_timeout():
    engine = SimpleIsolationEngine(timeout=0.1)
    code = "import time\ntime.sleep(1)"
    with pytest.raises(TimeoutError):
        await engine.execute_sandbox(code)

@pytest.mark.asyncio
async def test_isolation_manager_unsafe():
    engine = SimpleIsolationEngine()
    # Attempting to import os (which is restricted in a true sandbox, 
    # but here we just check if it runs or fails gracefully)
    code = "import os\nprint(os.getpid() if hasattr(os, 'getpid') else 'no_pid')"
    result = await engine.execute_sandbox(code)
    assert result is not None
    # Depending on the sandbox level, this might actually succeed or fail.
    # We just ensure it doesn't crash the manager.

@pytest.mark.asyncio
async def test_arc_agent_verify():
    agent = ARCAgent()
    program = PeARLProgram(source_code="def transform(grid):\n    return grid", confidence=1.0)
    train_examples = [
        {"input": [[1]], "output": [[1]]}
    ]
    # ARCAgent uses self.reasoning (ArcReasoningEngine) which has search_engine (NeuroSymbolicSearch)
    score = await agent.reasoning.search_engine._verify_correctness(program.source_code, train_examples)
    assert score == 1.0
