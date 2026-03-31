"""
SandboxActuator — Docker-Sandbox backed ActuatorProtocol
=========================================================
Bridges DockerSandbox ↔ SwarmManager.dispatch() via ActuatorProtocol.

Usage:
    from cortex.swarm.actuators.sandbox import SandboxActuator

    actuator = SandboxActuator()
    manager.register_actuator("sandbox", actuator)

    # Auto-allow for Tier 0/1:
    response = await manager.dispatch("sandbox", "ls /tmp")

    # Elevated — requires approval_token in context:
    response = await manager.dispatch(
        "sandbox",
        "pip install httpx",
        context={"approval_token": "<ledger_issued_token>"},
    )
"""
from __future__ import annotations

import logging
from typing import Any

from cortex.execution.risk import RiskTier
from cortex.execution.sandbox import DockerSandbox, SandboxBlocked, SandboxResult
from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse

logger = logging.getLogger("cortex.swarm.actuators.sandbox")


class SandboxActuator:
    """
    Ω-governed sandbox actuator.

    Implements ActuatorProtocol. Wraps DockerSandbox and
    converts SandboxResult → ActuatorResponse for the SwarmManager.
    """

    provider_id: str = "cortex-sandbox"

    def __init__(
        self,
        image: str = "python:3.12-slim",
        timeout: int = 30,
        max_output_bytes: int = 128_000,
    ) -> None:
        self._sandbox = DockerSandbox(image=image, timeout=timeout)
        self._max_output = max_output_bytes

    async def health_check(self) -> bool:
        """Verify Docker is available."""
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
            return proc.returncode == 0
        except Exception:
            return False

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> ActuatorResponse:
        ctx = context or {}
        approval_token: str | None = ctx.get("approval_token")

        try:
            result: SandboxResult = await self._sandbox.execute(
                task,
                approval_token=approval_token,
            )
        except SandboxBlocked as e:
            logger.error("SandboxActuator: BLOCKED — %s", e)
            return ActuatorResponse(
                content="",
                metadata={"tier": "CRITICAL", "blocked": True},
                status="failed",
                error=str(e),
            )

        if result.blocked:
            return ActuatorResponse(
                content="",
                metadata={
                    "tier": result.tier.name,
                    "block_reason": result.block_reason,
                    "blocked": True,
                },
                status="failed",
                error=result.block_reason,
            )

        # Truncate large outputs (Shannon compaction)
        stdout = result.stdout[: self._max_output]
        stderr = result.stderr[:4096]

        status = "success" if result.success else "failed"

        return ActuatorResponse(
            content=stdout,
            metadata={
                "tier": result.tier.name,
                "exit_code": result.exit_code,
                "stderr": stderr,
                "container_name": result.container_name,
                "duration_ms": result.duration_ms,
                "auto_allowed": result.tier <= RiskTier.MONITORED,
            },
            status=status,
            error=stderr if not result.success else None,
            reproducibility_level="deterministic",
        )
