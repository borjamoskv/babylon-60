# [C5-REAL] Exergy-Maximized
"""CORTEX Runtime — Built-in Agents.

Two real agents that demonstrate the full Orchestrator ↔ StateVector loop:

1. HealthMonitorAgent (daemon)
   - Periodically polls system state from the orchestrator
   - Emits health events to the EventBus
   - Detects anomalies and triggers recovery

2. TaskWorkerAgent (reactive)
   - Receives TASK_REQUEST messages
   - Processes tasks (simulated work)
   - Reports results back via the Orchestrator
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind

logger = logging.getLogger("cortex.runtime.agents")


# ─── Agent 1: Health Monitor (Daemon) ─────────────────────────────


class HealthMonitorAgent(BaseAgent):
    """Daemon agent that monitors system health.

    Runs in tick() mode — no incoming messages needed.
    Periodically:
        1. Reads the SystemStateVector snapshot
        2. Evaluates health conditions
        3. Emits events on the EventBus if anomalies detected
        4. Records telemetry

    This is a REAL agent that participates in the orchestrator loop.
    """

    def __init__(
        self,
        bus: Any,
        orchestrator: Any = None,  # Set post-init to avoid circular
        check_interval_s: float = 5.0,
    ) -> None:
        manifest = AgentManifest(
            agent_id="health-monitor",
            purpose="Monitor system health and emit anomaly events",
            daemon=True,
            tools_allowed=["system_status"],
            max_consecutive_errors=5,
        )
        super().__init__(manifest=manifest, bus=bus)
        self.orchestrator = orchestrator
        self._check_interval = check_interval_s
        self._last_check: float = 0.0
        self._checks_performed: int = 0
        self._anomalies_detected: int = 0

    async def on_start(self) -> None:
        logger.info("[health-monitor] Daemon started (interval=%.1fs)", self._check_interval)

    async def handle_message(self, message: AgentMessage) -> None:
        """Handle direct commands (e.g., force check, reconfigure)."""
        if message.kind == MessageKind.TASK_REQUEST:
            cmd = message.payload.get("objective", "")
            if cmd == "force_check":
                await self._run_health_check()
            elif cmd == "set_interval":
                new_interval = message.payload.get("input", {}).get(
                    "interval", self._check_interval
                )
                self._check_interval = float(new_interval)
                logger.info("[health-monitor] Interval updated to %.1fs", self._check_interval)

    async def tick(self) -> None:
        """Periodic health check — this is where the daemon does its work."""
        now = time.monotonic()
        if (now - self._last_check) >= self._check_interval:
            await self._run_health_check()
            self._last_check = now

    async def _run_health_check(self) -> None:
        """Execute a single health check cycle."""
        self._checks_performed += 1

        if self.orchestrator is None:
            return

        state = self.orchestrator.state
        snapshot = state.snapshot()

        # Store in working memory for history
        self.memory.scratchpad["last_check"] = snapshot
        self.memory.scratchpad["checks_total"] = self._checks_performed

        # Anomaly detection rules
        anomalies: list[str] = []

        if snapshot["error_pressure"] > 0.5:
            anomalies.append(f"HIGH_ERROR_PRESSURE: {snapshot['error_pressure']:.3f}")

        if snapshot["entropy"] > 0.6:
            anomalies.append(f"HIGH_ENTROPY: {snapshot['entropy']:.3f}")

        if snapshot["agents_active"] == 0 and snapshot["tasks_pending"] > 0:
            anomalies.append(
                f"ORPHANED_TASKS: {snapshot['tasks_pending']} tasks with 0 active agents"
            )

        if anomalies:
            self._anomalies_detected += len(anomalies)
            logger.warning(
                "[health-monitor] Anomalies detected: %s",
                anomalies,
            )
            # Emit to EventBus for the orchestrator to process
            await self.orchestrator.event_bus.publish(
                "system.error",
                {
                    "event_type": "system.error",
                    "source": self.agent_id,
                    "anomalies": anomalies,
                    "snapshot": snapshot,
                },
            )
        else:
            logger.debug(
                "[health-monitor] Check #%d OK — phase=%s entropy=%.3f",
                self._checks_performed,
                snapshot["phase"],
                snapshot["entropy"],
            )

    def get_telemetry(self) -> dict[str, Any]:
        """Return health monitor telemetry."""
        return {
            "checks_performed": self._checks_performed,
            "anomalies_detected": self._anomalies_detected,
            "check_interval_s": self._check_interval,
            "last_check": self.memory.scratchpad.get("last_check"),
        }


# ─── Agent 2: Task Worker (Reactive) ──────────────────────────────


class TaskWorkerAgent(BaseAgent):
    """Reactive agent that processes task requests.

    Lifecycle:
        1. Receives TASK_REQUEST via message bus
        2. Processes the task (calls registered handler)
        3. Reports success/failure back to the orchestrator

    Handlers are registered at init time and dispatched by objective prefix.
    Default handler: echo the input back.
    """

    def __init__(
        self,
        agent_id: str,
        bus: Any,
        orchestrator: Any = None,
        purpose: str = "General task worker",
    ) -> None:
        manifest = AgentManifest(
            agent_id=agent_id,
            purpose=purpose,
            daemon=False,
            tools_allowed=[],
            max_consecutive_errors=3,
        )
        super().__init__(manifest=manifest, bus=bus)
        self.orchestrator = orchestrator
        self._handlers: dict[str, Any] = {}
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0

    def register_handler(self, prefix: str, handler: Any) -> None:
        """Register a task handler for objectives starting with prefix."""
        self._handlers[prefix] = handler
        logger.info("[%s] Registered handler for '%s'", self.agent_id, prefix)

    async def on_start(self) -> None:
        logger.info("[%s] Task worker ready (handlers=%d)", self.agent_id, len(self._handlers))

    async def handle_message(self, message: AgentMessage) -> None:
        """Process incoming task requests."""
        if message.kind != MessageKind.TASK_REQUEST:
            logger.debug("[%s] Ignoring message kind: %s", self.agent_id, message.kind.value)
            return

        task_id = message.payload.get("task_id", "unknown")
        objective = message.payload.get("objective", "")
        input_data = message.payload.get("input", {})

        logger.info("[%s] Processing task '%s': %s", self.agent_id, task_id, objective)

        self.memory.active_tasks.append(task_id)

        try:
            # Find matching handler
            handler = self._find_handler(objective)
            result = await handler(objective, input_data)

            self._tasks_completed += 1

            # Report success
            if self.orchestrator:
                await self.orchestrator.report_task_completed(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    output={"result": result},
                )

            # Send result back to requester
            await self.send_result(
                recipient=message.sender,
                result=result,
                correlation_id=message.correlation_id,
            )

            logger.info("[%s] Task '%s' completed", self.agent_id, task_id)

        except Exception as exc:
            self._tasks_failed += 1
            error_msg = f"{type(exc).__name__}: {exc}"

            # Report failure
            if self.orchestrator:
                await self.orchestrator.report_task_failed(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    error=error_msg,
                )

            logger.error("[%s] Task '%s' failed: %s", self.agent_id, task_id, error_msg)
        finally:
            if task_id in self.memory.active_tasks:
                self.memory.active_tasks.remove(task_id)

    def _find_handler(self, objective: str) -> Any:
        """Find the handler matching the objective prefix."""
        for prefix, handler in self._handlers.items():
            if objective.startswith(prefix):
                return handler
        return self._default_handler

    @staticmethod
    async def _default_handler(objective: str, input_data: dict) -> dict:
        """Default handler: echo the input with metadata."""
        # Simulate some work
        await asyncio.sleep(0.01)
        return {
            "objective_received": objective,
            "input_received": input_data,
            "handler": "default_echo",
            "timestamp": time.time(),
        }

    def get_telemetry(self) -> dict[str, Any]:
        """Return task worker telemetry."""
        return {
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "active_tasks": list(self.memory.active_tasks),
            "handlers": list(self._handlers.keys()),
        }
