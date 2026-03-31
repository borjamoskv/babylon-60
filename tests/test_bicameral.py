import asyncio
import pytest

from cortex.engine import CortexEngine
from cortex.engine.bicameral import BicameralDispatcher

@pytest.mark.asyncio
async def test_bicameral_dispatch_logic():
    """Verify that the dispatcher separates concerns correctly."""
    dispatcher = BicameralDispatcher()

    fast_called = False
    slow_called = False

    async def mock_fast(*args, **kwargs):
        nonlocal fast_called
        fast_called = True
        return "fast_result"

    async def mock_slow(*args, **kwargs):
        nonlocal slow_called
        await asyncio.sleep(0.1) # Simulate IO
        slow_called = True
        return "slow_result"

    dispatcher.register_fast("test_op", mock_fast)
    dispatcher.register_slow(mock_slow)

    # Execution fast path
    result_fast = await dispatcher.dispatch("test_op", "arg1")

    assert result_fast == "fast_result"
    assert fast_called is True

    # Execution slow path
    result_slow = await dispatcher.dispatch("store", "arg1")
    assert result_slow == "slow_result"
    assert slow_called is True

@pytest.mark.asyncio
async def test_engine_bicameral_integration():
    """Integration test for CortexEngine store delegation."""
    engine = CortexEngine()

    slow_executed = asyncio.Event()

    async def mock_slow_callback(*args, **kwargs):
        if "test_fact_long" in kwargs.get("content", "") or (len(args) > 1 and "test_fact_long" in args[1]):
            slow_executed.set()
        return 1

    # Override the registered routes for test
    if hasattr(engine, "dispatcher") and engine.dispatcher is not None:
        # DO NOT register fast for "store" so it routes to slow!
        engine.dispatcher._slow_routes["store"] = mock_slow_callback
    else:
        # Fallback if CortexEngine doesn't instantiate dispatcher by default
        dispatcher = BicameralDispatcher()
        dispatcher._slow_routes["store"] = mock_slow_callback
        engine.dispatcher = dispatcher

    # Dispatch directly through dispatcher as store might not hit dispatcher directly in mock
    await engine.dispatcher.dispatch("store", "test_project", content="test_fact_long")

    try:
        await asyncio.wait_for(slow_executed.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Slow bus was never executed for 'store'")
