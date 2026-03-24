from typing import Any

import pytest

from cortex.swarm.actuators.protocol import ActuatorResponse
from cortex.swarm.manager import SwarmManager


class MockActuator:
    def __init__(self, provider_id: str) -> None:
        self._provider_id = provider_id

    async def execute(self, task: str, context: dict[str, Any]) -> ActuatorResponse:
        return ActuatorResponse(content=f"Executed: {task}", metadata={"source": self._provider_id})

    async def health_check(self) -> bool:
        return True

    @property
    def provider_id(self) -> str:
        return self._provider_id


@pytest.mark.asyncio
async def test_swarm_manager_privacy_masking():
    manager = SwarmManager()
    actuator = MockActuator("test-provider")
    manager.register_actuator("test", actuator)

    # Task with sensitive info (email and IP)
    task = "Send email to admin@cortex.com from 192.168.1.1"
    response = await manager.dispatch("test", task)

    assert "[MASKED_EMAIL]" in response["content"]
    assert "[MASKED_IPV4]" in response["content"]
    assert "admin@cortex.com" not in response["content"]


@pytest.mark.asyncio
async def test_swarm_manager_dispatch_error():
    manager = SwarmManager()
    # Unregistered actuator
    with pytest.raises(ValueError, match="Unknown actuator"):
        await manager.dispatch("non-existent", "task")
