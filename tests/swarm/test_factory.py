from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.ledger.core import SovereignLedger
from cortex.swarm.discovery import SkillRegistry
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager


@pytest.fixture
def mock_ledger():
    ledger = MagicMock(spec=SovereignLedger)
    ledger.record_transaction = AsyncMock()
    return ledger

@pytest.fixture
def mock_registry():
    registry = MagicMock(spec=SkillRegistry)
    registry.list_by_category.return_value = []
    # Mock para asegurar que list_by_category devuelve algo iterable
    return registry

@pytest.fixture
def mock_manager(mock_ledger, mock_registry):
    manager = MagicMock(spec=SwarmManager)
    manager.ledger = mock_ledger
    manager.registry = mock_registry
    manager.bus = MagicMock()
    manager.register_actuator = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_factory_initialization(mock_registry, mock_manager):
    factory = SwarmFactory(manager=mock_manager)
    assert "P0" in factory.QUADRANTS

@pytest.mark.asyncio
async def test_recruit_squad(mock_registry, mock_manager):
    # Setup mock to return some skills
    mock_skill = MagicMock()
    mock_skill.name = "test_specialist"
    mock_registry.list_by_category.return_value = [mock_skill]

    factory = SwarmFactory(manager=mock_manager)

    agent_ids = await factory.recruit_squad("P0", size=1)

    assert len(agent_ids) == 1
    assert agent_ids[0].startswith("P0-")
    mock_manager.register_actuator.assert_called_once()

    justification = factory.justify_recruitment("P0", agent_ids)
    assert "Exergy Target: 12.5" in justification
    assert "Estimated Yield: 12.5" in justification

def test_get_quadrant_skills(mock_registry, mock_manager):
    mock_skill = MagicMock()
    mock_skill.name = "test_skill"
    mock_registry.list_by_category.return_value = [mock_skill]

    factory = SwarmFactory(manager=mock_manager)
    skills = factory.get_quadrant_skills("P0")

    # Due to dedup logic and P0 having 5 categories, it might return multiple if mocked per category,
    # but here we mock it once.
    assert "test_skill" in skills
