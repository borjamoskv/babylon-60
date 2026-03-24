from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ActuatorProtocol(Protocol):
    """
    Sovereign Protocol for External Agent Actuators (Ω-Architecture).

    Every external agent (Devin, Claude, Operator, etc.) must implement
    this protocol to be governed by CORTEX.
    """

    async def execute(
        self, task: str, context: dict[str, Any], task_id: str | None = None
    ) -> ActuatorResponse:
        """Execute a task and return a validated response."""
        ...

    async def health_check(self) -> bool:
        """Verify the health and availability of the external provider."""
        ...

    @property
    def provider_id(self) -> str:
        """Name of the external provider (e.g., 'openai-operator', 'claude-code')."""
        ...


class ActuatorResponse(dict[str, Any]):
    """Structured response from an external actuator including trust metadata."""

    def __init__(
        self,
        content: str,
        metadata: dict[str, Any],
        status: str = "success",
        error: str | None = None,
    ) -> None:
        super().__init__(
            {
                "content": content,
                "metadata": metadata,
                "status": status,
                "error": error,
                "correlation_id": str(uuid.uuid4()),
            }
        )
