# [C5-REAL] Exergy-Maximized

import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from babylon60.extensions.daemon.daemon_omega import DaemonOmega
from babylon60.engine.causal.belief_objects import BeliefState

class MockBeliefStore:
    def __init__(self):
        self.deleted_states = []
        self.delete_count = 5

    async def delete_by_states(self, states: list[str]) -> int:
        self.deleted_states.extend(states)
        return self.delete_count

@pytest.mark.asyncio
async def test_macrophage_cycle():
    mock_store = MockBeliefStore()
    daemon = DaemonOmega(store=mock_store, interval_seconds=1, auto_commit=False)
    
    purged = await daemon._macrophage_cycle()
    
    assert purged == 5
    assert BeliefState.DISCARDED.value in mock_store.deleted_states
    assert BeliefState.ORPHANED.value in mock_store.deleted_states

@patch("subprocess.check_output")
@patch("subprocess.run")
def test_git_sentinel_commit_with_changes(mock_run, mock_check_output):
    mock_store = MockBeliefStore()
    daemon = DaemonOmega(store=mock_store, interval_seconds=1, auto_commit=True)
    
    # Simulate uncommitted changes
    mock_check_output.return_value = " M some_file.py"
    
    daemon._git_sentinel_commit(purged=5)
    
    mock_check_output.assert_called_once()
    assert mock_run.call_count == 2 # git add . AND git commit

@patch("subprocess.check_output")
@patch("subprocess.run")
def test_git_sentinel_commit_no_changes(mock_run, mock_check_output):
    mock_store = MockBeliefStore()
    daemon = DaemonOmega(store=mock_store, interval_seconds=1, auto_commit=True)
    
    # Simulate clean working directory
    mock_check_output.return_value = ""
    
    daemon._git_sentinel_commit(purged=5)
    
    mock_check_output.assert_called_once()
    mock_run.assert_not_called()

@pytest.mark.asyncio
async def test_run_loop_shutdown():
    mock_store = MockBeliefStore()
    daemon = DaemonOmega(store=mock_store, interval_seconds=0.01, auto_commit=False)
    
    # Fire and forget the task
    task = asyncio.create_task(daemon.run_loop())
    
    # Let it run one iteration
    await asyncio.sleep(0.02)
    
    # Stop
    daemon.stop()
    await task
    
    assert mock_store.deleted_states  # It should have executed the cycle at least once
