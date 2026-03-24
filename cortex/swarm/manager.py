from __future__ import annotations

import hashlib
import logging
from typing import Any

from cortex.engine.ledger import SovereignLedger
from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse
from cortex.swarm.guards.privacy_gate import PrivacyGate

logger = logging.getLogger("cortex.swarm.manager")


class SwarmManager:
    """
    Sovereign Swarm Orchestrator (Ω-Architecture).

    Manages a collection of governed actuators, enforcing privacy
    guards and ledger logging for every external interaction.
    """

    def __init__(self, ledger: SovereignLedger | None = None) -> None:
        self.actuators: dict[str, ActuatorProtocol] = {}
        self.privacy_gate = PrivacyGate()
        self.ledger = ledger

    def register_actuator(self, name: str, actuator: ActuatorProtocol) -> None:
        """Register a new governed actuator."""
        self.actuators[name] = actuator
        logger.info("SwarmManager: Registered actuator '%s' (%s)", name, actuator.provider_id)

    async def dispatch(
        self, actuator_name: str, task: str, context: dict[str, Any] | None = None
    ) -> ActuatorResponse:
        """
        Dispatch a task to a registered actuator with privacy enforcement and ledger audit.
        """
        if actuator_name not in self.actuators:
            raise ValueError(f"Unknown actuator: {actuator_name}")

        actuator = self.actuators[actuator_name]
        ctx = context or {}

        # 1. Privacy Filter (Ω-Guard)
        sanitized = self.privacy_gate.validate_outgoing(task, ctx)

        # 2. Ledger Audit (Audit Trail pre-execution)
        ledger = self.ledger
        if ledger:
            audit_data = {
                "actuator": actuator_name,
                "provider": actuator.provider_id,
                "task_hash": hashlib.sha256(task.encode()).hexdigest(),
                "sanitized_task_hash": hashlib.sha256(sanitized["task"].encode()).hexdigest(),
                "privacy_applied": True,
            }
            await ledger.record_transaction(
                project="swarm", action="dispatch_attempt", detail=audit_data
            )

        logger.info("SwarmManager: Dispatching to %s...", actuator_name)

        # 3. Execution via Governed Actuator
        try:
            response = await actuator.execute(task=sanitized["task"], context=sanitized["context"])

            # 4. Ledger Audit (Post-execution)
            ledger = self.ledger
            if ledger and response["status"] == "success":
                await ledger.record_transaction(
                    project="swarm",
                    action="execution_success",
                    detail={
                        "actuator": actuator_name,
                        "correlation_id": response.get("correlation_id"),
                        "content_hash": hashlib.sha256(response["content"].encode()).hexdigest(),
                    },
                )

            return response
        except Exception as e:
            logger.error("SwarmManager: Execution failed on %s: %s", actuator_name, e)
            if ledger:
                await ledger.record_transaction(
                    project="swarm",
                    action="execution_failure",
                    detail={"actuator": actuator_name, "error": str(e)},
                )
            return ActuatorResponse(content="", metadata={}, status="failed", error=str(e))

    async def list_available(self) -> list[str]:
        """Check health and list all available actuators."""
        available = []
        for name, actuator in self.actuators.items():
            if await actuator.health_check():
                available.append(name)
        return available
