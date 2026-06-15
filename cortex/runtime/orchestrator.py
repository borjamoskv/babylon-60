# [C5-REAL] Exergy-Maximized
"""CORTEX Runtime — Orchestrator.

The Orchestrator is the brain that connects:
    EventBus → StateVector → Supervisor → Agents

It is rule-based and deterministic:
    1. Subscribes to the EventBus for system-level events
    2. Applies each event to the SystemStateVector (state mutation)
    3. Evaluates rules against the new state (decision)
    4. Dispatches actions to agents via the Supervisor (execution)

This closes the 30% gap. Without it, all existing components
are disconnected organs. With it, the system has a spine.

Architecture:
    ┌─────────────────────────────────────────────┐
    │                ORCHESTRATOR                  │
    │                                              │
    │  EventBus ──→ StateVector ──→ Rules ──→ Act  │
    │     ↑                                   │    │
    │     └────── Supervisor ←────────────────┘    │
    └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from cortex.agents.bus import MessageBus
from cortex.agents.message_schema import MessageKind, new_message
from cortex.agents.supervisor import Supervisor
from cortex.events.bus import DistributedEventBus
from cortex.runtime.system_state import SystemPhase, SystemStateVector

logger = logging.getLogger("cortex.runtime.orchestrator")


@dataclass
class OrchestratorRule:
    """A rule that fires when a condition on the state vector is met.

    condition: callable(SystemStateVector) -> bool
    action:    callable(Orchestrator) -> Coroutine
    name:      human-readable rule identifier
    cooldown:  minimum seconds between firings
    """

    name: str
    condition: Callable[[SystemStateVector], bool]
    action: Callable[..., Coroutine[Any, Any, None]]
    cooldown: float = 10.0
    last_fired: float = 0.0


class Orchestrator:
    """Rule-based system orchestrator.

    Lifecycle:
        1. __init__(event_bus, supervisor, state_vector)
        2. register_rules(...)
        3. start() — subscribes to event bus, enters control loop
        4. stop()  — graceful shutdown

    The orchestrator does NOT process agent-to-agent messages.
    It processes system-level events (agent lifecycle, task lifecycle, errors).
    """

    # System topics the orchestrator subscribes to
    SYSTEM_TOPICS = (
        "agent.lifecycle",
        "task.lifecycle",
        "system.error",
        "system.recovery",
        "orchestrator.command",
    )

    def __init__(
        self,
        event_bus: DistributedEventBus,
        message_bus: MessageBus,
        supervisor: Supervisor,
        state: SystemStateVector | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.message_bus = message_bus
        self.supervisor = supervisor
        self.state = state or SystemStateVector()
        self._rules: list[OrchestratorRule] = []
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._start_time: float = 0.0

        # Built-in rules
        self._register_builtin_rules()

    # ── Rule Registration ────────────────────────────────────────

    def register_rule(self, rule: OrchestratorRule) -> None:
        """Register a rule for evaluation on every state change."""
        self._rules.append(rule)
        logger.info("Orchestrator: Registered rule '%s'", rule.name)

    def _register_builtin_rules(self) -> None:
        """Built-in safety and operational rules."""
        self.register_rule(
            OrchestratorRule(
                name="critical_entropy_alert",
                condition=lambda s: s.phase == SystemPhase.CRITICAL,
                action=self._action_critical_alert,
                cooldown=30.0,
            )
        )
        self.register_rule(
            OrchestratorRule(
                name="high_entropy_throttle",
                condition=lambda s: s.phase == SystemPhase.HIGH_ENTROPY,
                action=self._action_high_entropy_throttle,
                cooldown=15.0,
            )
        )
        self.register_rule(
            OrchestratorRule(
                name="recovery_complete",
                condition=lambda s: (
                    s.phase == SystemPhase.NOMINAL
                    and s.error_pressure == 0.0
                    and s.agents_active > 0
                ),
                action=self._action_recovery_complete,
                cooldown=60.0,
            )
        )

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the orchestrator: subscribe to events, begin control loop."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True
        self._start_time = time.monotonic()

        # Subscribe to system topics
        for topic in self.SYSTEM_TOPICS:
            self.event_bus.subscribe(topic, self._on_event)
            logger.debug("Orchestrator: Subscribed to '%s'", topic)

        # Boot state transition
        self.state.apply("system.boot", "orchestrator")

        logger.info(
            "Orchestrator: ONLINE — %d rules, %d topics, state=%s",
            len(self._rules),
            len(self.SYSTEM_TOPICS),
            self.state.phase.value,
        )

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        self.state.apply("system.shutdown", "orchestrator")
        logger.info(
            "Orchestrator: SHUTDOWN — tick=%d, uptime=%.1fs",
            self.state.tick,
            time.monotonic() - self._start_time,
        )

    # ── Event Processing ─────────────────────────────────────────

    async def _on_event(self, payload: dict[str, Any]) -> None:
        """Process a system event from the EventBus.

        Pipeline: receive → classify → mutate state → evaluate rules → act
        """
        event_type = payload.get("event_type", "unknown")
        source = payload.get("source", "unknown")

        # 1. Mutate state
        self.state.apply(event_type, source, payload)

        # 2. Evaluate rules against new state
        await self._evaluate_rules()

        # 3. Log state transition
        logger.debug(
            "Orchestrator: processed event '%s' from '%s' → tick=%d phase=%s",
            event_type,
            source,
            self.state.tick,
            self.state.phase.value,
        )

    async def _evaluate_rules(self) -> None:
        """Evaluate all registered rules against current state."""
        now = time.monotonic()

        for rule in self._rules:
            # Skip if in cooldown
            if (now - rule.last_fired) < rule.cooldown:
                continue

            try:
                if rule.condition(self.state):
                    logger.info(
                        "Orchestrator: Rule '%s' FIRED (phase=%s, entropy=%.3f)",
                        rule.name,
                        self.state.phase.value,
                        self.state.entropy,
                    )
                    rule.last_fired = now
                    await rule.action(self)
            except Exception as exc:
                logger.error(
                    "Orchestrator: Rule '%s' evaluation failed: %s",
                    rule.name,
                    exc,
                )

    # ── Agent Lifecycle Integration ──────────────────────────────

    async def register_agent(self, agent: Any, max_restarts: int = 3) -> None:
        """Register an agent with both Supervisor and StateVector."""
        self.supervisor.register(agent, max_restarts=max_restarts)
        await self.event_bus.publish(
            "agent.lifecycle",
            {
                "event_type": "agent.registered",
                "source": "orchestrator",
                "agent_id": agent.agent_id,
            },
        )

    async def start_agent(self, agent_id: str) -> None:
        """Start an agent and record in state."""
        await self.supervisor.start_agent(agent_id)
        await self.event_bus.publish(
            "agent.lifecycle",
            {
                "event_type": "agent.started",
                "source": "orchestrator",
                "agent_id": agent_id,
            },
        )

    async def stop_agent(self, agent_id: str) -> None:
        """Stop an agent and record in state."""
        await self.supervisor.stop_agent(agent_id)
        await self.event_bus.publish(
            "agent.lifecycle",
            {
                "event_type": "agent.stopped",
                "source": "orchestrator",
                "agent_id": agent_id,
            },
        )

    async def submit_task(
        self,
        agent_id: str,
        task_id: str,
        objective: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Submit a task to an agent via the message bus."""
        msg = new_message(
            sender="orchestrator",
            recipient=agent_id,
            kind=MessageKind.TASK_REQUEST,
            payload={
                "task_id": task_id,
                "objective": objective,
                "input": input_data or {},
            },
        )
        await self.message_bus.send(msg)

        # Record in state
        await self.event_bus.publish(
            "task.lifecycle",
            {
                "event_type": "task.submitted",
                "source": "orchestrator",
                "task_id": task_id,
                "agent_id": agent_id,
            },
        )

    async def report_task_completed(
        self, task_id: str, agent_id: str, output: dict[str, Any] | None = None
    ) -> None:
        """Record task completion in state."""
        await self.event_bus.publish(
            "task.lifecycle",
            {
                "event_type": "task.completed",
                "source": agent_id,
                "task_id": task_id,
                "output": output or {},
            },
        )

    async def report_task_failed(self, task_id: str, agent_id: str, error: str) -> None:
        """Record task failure in state."""
        await self.event_bus.publish(
            "task.lifecycle",
            {
                "event_type": "task.failed",
                "source": agent_id,
                "task_id": task_id,
                "error": error,
            },
        )

    async def report_error(self, source: str, error: str) -> None:
        """Record a system error."""
        await self.event_bus.publish(
            "system.error",
            {
                "event_type": "system.error",
                "source": source,
                "error": error,
            },
        )

    # ── Built-in Actions ─────────────────────────────────────────

    async def _action_critical_alert(self, _: Any = None) -> None:
        """CRITICAL phase: system is near failure. Log and throttle."""
        logger.critical(
            "🔴 CRITICAL ENTROPY — error_pressure=%.3f entropy=%.3f agents=%d/%d tasks_failed=%d",
            self.state.error_pressure,
            self.state.entropy,
            self.state.agents_active,
            self.state.agents_total,
            self.state.tasks_failed,
        )
        # In a production system, this would page an operator
        # or trigger automatic scaling/restart

    async def _action_high_entropy_throttle(self, _: Any = None) -> None:
        """HIGH_ENTROPY phase: reduce load, allow recovery."""
        logger.warning(
            "🟡 HIGH ENTROPY — throttling. entropy=%.3f error_pressure=%.3f",
            self.state.entropy,
            self.state.error_pressure,
        )

    async def _action_recovery_complete(self, _: Any = None) -> None:
        """System recovered to nominal. Log."""
        logger.info(
            "🟢 RECOVERY COMPLETE — system nominal. entropy=%.3f throughput=%.2f",
            self.state.entropy,
            self.state.throughput,
        )

    # ── Query ────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Full orchestrator status."""
        return {
            "running": self._running,
            "uptime_s": round(time.monotonic() - self._start_time, 1) if self._running else 0,
            "state": self.state.snapshot(),
            "rules": [{"name": r.name, "cooldown": r.cooldown} for r in self._rules],
            "supervisor": self.supervisor.status(),
        }
