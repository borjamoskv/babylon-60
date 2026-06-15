# [C5-REAL] Exergy-Maximized

import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock
from cortex.guards.structural_isolation_guard import StructuralIsolationGuard

@pytest.fixture
def temp_workspace():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)

@pytest.mark.asyncio
async def test_structural_isolation_guard_valid(temp_workspace):
    guard = StructuralIsolationGuard(workspace_dir=temp_workspace)
    payload = {"content": "valid", "entropy_score": 10.0}
    is_valid = await guard.validate_payload(agent_id="test_agent", payload=payload)
    assert is_valid is True

@pytest.mark.asyncio
async def test_structural_isolation_guard_invalid(temp_workspace):
    mock_ledger = AsyncMock()
    guard = StructuralIsolationGuard(workspace_dir=temp_workspace, ledger_client=mock_ledger)
    payload = {"content": "too high entropy", "entropy_score": 30.0}
    is_valid = await guard.validate_payload(agent_id="test_agent", payload=payload)
    assert is_valid is False
    mock_ledger.emit_event.assert_called_once()

@pytest.mark.asyncio
async def test_structural_isolation_guard_exception_strict(temp_workspace):
    guard = StructuralIsolationGuard(workspace_dir=temp_workspace, strict_mode=True)
    is_valid = await guard.validate_payload(agent_id="test_agent", payload=None)
    assert is_valid is False

@pytest.mark.asyncio
async def test_structural_isolation_guard_exception_non_strict(temp_workspace):
    guard = StructuralIsolationGuard(workspace_dir=temp_workspace, strict_mode=False)
    is_valid = await guard.validate_payload(agent_id="test_agent", payload=None)
    assert is_valid is True
