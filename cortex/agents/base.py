"""CORTEX Agent Runtime — Base Agent.

BaseAgent provides the event loop, message handling, and lifecycle
management that distinguishes an agent from a tool.

Subclasses implement:
    - handle_message(message) — react to incoming messages
    - tick() — periodic autonomous work (daemons override this)

The loop: heartbeat → receive → handle_message/tick → repeat.
Auto-quarantine after max_consecutive_errors.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from cortex.agents.contracts import TaskErrorPayload, TaskRequestPayload, TaskResultPayload
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, MessagePayloadInput, new_message
from cortex.agents.middleware import AgentMiddleware
from cortex.agents.state import AgentState, AgentStatus, WorkingMemory
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.base")


class BaseAgent:
    """Abstract base agent with async event loop.

    Provides:
        - Continuous run loop with heartbeat
        - Message receive/dispatch
        - Automatic quarantine on repeated failures
        - Isolated WorkingMemory
        - Tool access governed by manifest policy
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,  # MessageBus protocol
        tool_registry: ToolRegistry | None = None,
        middlewares: list[AgentMiddleware] | None = None,
    ) -> None:
        self.manifest = manifest
        self.bus = bus
        self.tools = tool_registry or ToolRegistry()
        self.middlewares = list(middlewares or [])
        self.state = AgentState()
        self.memory = WorkingMemory()
        self._task: asyncio.Task[None] | None = None

    @property
    def agent_id(self) -> str:
        return self.manifest.agent_id

    def _azkartu_lyapunov_guard(self) -> None:
        """Azkartu Lyapunov-Control Protocol (v7.0 Sovereign Singularity).

        Enforces dV/dt < 0 condition (Thermodynamic Stability).
        If the internal state entropy increases (errors compounding), aborts.
        Provides C5-REAL simulation defense against stochastic hallucination.
        """
        # Calculate current Lyapunov function V(x) based on system entropy
        current_v = (self.state.consecutive_errors * 50) + (self.state.error_count * 10)

        if not hasattr(self, "_lyapunov_v"):
            self._lyapunov_v = current_v
            return

        dv_dt = current_v - self._lyapunov_v
        self._lyapunov_v = current_v

        if dv_dt > 0:
            logger.error(
                "[%s] [AZKARTU-ABORT] Lyapunov Instability detected (dV/dt = %d > 0).",
                self.agent_id,
                dv_dt,
            )
            raise RuntimeError(
                f"Azkartu Guard Triggered: System entropy increasing (dV/dt={dv_dt})"
            )

    # ── Abstract methods (subclasses implement) ──────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Process an incoming message. Subclasses MUST override."""
        raise NotImplementedError(f"{self.__class__.__name__} must implement handle_message()")

    async def tick(self) -> None:
        """Periodic autonomous work. Daemons override this.

        Default implementation is a no-op for reactive agents.
        """

    async def on_start(self) -> None:
        """Hook called once when the agent starts running."""

    async def on_stop(self) -> None:
        """Hook called once when the agent stops."""

    # ── Event loop ───────────────────────────────────────────────

    async def run(self) -> None:
        """Main event loop. Runs until stopped or quarantined."""
        self.state.status = AgentStatus.RUNNING
        logger.info("[%s] Agent started", self.agent_id)

        try:
            await self.on_start()
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] on_start failed: %s", self.agent_id, exc)
            self.state.status = AgentStatus.FAILED
            return

        while self.state.status == AgentStatus.RUNNING:
            current_message: AgentMessage | None = None
            step_kind = "tick"
            try:
                self.state.last_heartbeat_ts = time.time()

                # Azkartu Lyapunov-Control Guard (v7.0 Sovereign Singularity)
                self._azkartu_lyapunov_guard()

                # Try to receive a message
                msg = await self.bus.receive(self.agent_id, timeout=1.0)
                current_message = msg

                if msg is not None:
                    # Handle shutdown signals
                    if msg.kind == MessageKind.SHUTDOWN:
                        logger.info("[%s] Received SHUTDOWN", self.agent_id)
                        break

                    step_kind = "message"
                    await self._emit_before_step(step_kind=step_kind, message=msg)
                    await self.handle_message(msg)
                    await self._emit_after_step(step_kind=step_kind, message=msg)
                    self.state.record_message_processed()
                    self.state.record_success()
                else:
                    # No message — run periodic tick
                    await self._emit_before_step(step_kind=step_kind, message=None)
                    await self.tick()
                    await self._emit_after_step(step_kind=step_kind, message=None)
                    self.state.record_success()

            except Exception as exc:  # noqa: BLE001
                self.state.record_error(repr(exc))
                await self._emit_after_step(
                    step_kind=step_kind,
                    message=current_message,
                    error=repr(exc),
                )
                await self._emit_retry(
                    error=repr(exc),
                    message=current_message,
                    consecutive_errors=self.state.consecutive_errors,
                )
                logger.warning(
                    "[%s] Error (consecutive=%d): %s",
                    self.agent_id,
                    self.state.consecutive_errors,
                    exc,
                )

                # Auto-quarantine after too many consecutive errors
                if self.state.consecutive_errors >= self.manifest.max_consecutive_errors:
                    self.state.status = AgentStatus.QUARANTINED
                    logger.error(
                        "[%s] QUARANTINED after %d consecutive errors",
                        self.agent_id,
                        self.state.consecutive_errors,
                    )
                    break

                # Brief backoff before retrying
                await asyncio.sleep(0.5)

        # Cleanup — preserve terminal statuses (QUARANTINED, FAILED)
        try:
            await self.on_stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("[%s] on_stop failed: %s", self.agent_id, exc)

        if self.state.status not in (
            AgentStatus.QUARANTINED,
            AgentStatus.FAILED,
        ):
            self.state.status = AgentStatus.IDLE

        logger.info(
            "[%s] Agent stopped (status=%s, msgs=%d, errors=%d)",
            self.agent_id,
            self.state.status.value,
            self.state.total_messages_processed,
            self.state.error_count,
        )

    # ── Lifecycle control ────────────────────────────────────────

    async def start(self) -> asyncio.Task[None]:
        """Start the agent as an asyncio task."""
        if self._task is not None and not self._task.done():
            raise RuntimeError(f"Agent {self.agent_id} is already running")
        self._task = asyncio.create_task(self.run(), name=f"agent-{self.agent_id}")
        return self._task

    async def stop(self) -> None:
        """Request graceful shutdown via message bus."""
        shutdown_msg = new_message(
            sender="supervisor",
            recipient=self.agent_id,
            kind=MessageKind.SHUTDOWN,
            payload={},
        )
        await self.bus.send(shutdown_msg)

    def force_stop(self) -> None:
        """Force-cancel the agent task."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            # Preserve terminal statuses set by supervisor/quarantine
            if self.state.status not in (
                AgentStatus.QUARANTINED,
                AgentStatus.FAILED,
            ):
                self.state.status = AgentStatus.IDLE

    # ── Tool access (policy-governed) ────────────────────────────

    async def use_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a tool respecting manifest policy."""
        tool = self.tools.get(tool_name, allowed=self.manifest.tools_allowed or None)
        await self._emit_tool_call(tool_name=tool_name, arguments=kwargs)
        try:
            result = await tool.execute(**kwargs)
        except Exception as exc:
            await self._emit_tool_result(
                tool_name=tool_name,
                arguments=kwargs,
                error=repr(exc),
            )
            raise
        await self._emit_tool_result(
            tool_name=tool_name,
            arguments=kwargs,
            result=result,
        )
        return result

    # ── Messaging helpers ────────────────────────────────────────

    async def send_result(
        self,
        recipient: str,
        result: Any,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Send a legacy untyped task result to another agent."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_RESULT,
            payload={"result": result},
            correlation_id=correlation_id if correlation_id is not None else "auto",
        )
        await self.bus.send(msg)

    async def send_task_result(
        self,
        recipient: str,
        op: str,
        result: Any,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Send a typed task result envelope to another agent."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_RESULT,
            payload=TaskResultPayload[Any](op=op, result=result),
            correlation_id=correlation_id if correlation_id is not None else "auto",
        )
        await self.bus.send(msg)

    async def send_task_error(
        self,
        recipient: str,
        error: str,
        *,
        op: str | None = None,
        supported: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Send a typed task error envelope to another agent."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_RESULT,
            payload=TaskErrorPayload(error=error, op=op, supported=supported),
            correlation_id=correlation_id if correlation_id is not None else "auto",
        )
        await self.bus.send(msg)

    async def request_task(
        self,
        recipient: str,
        task_payload: TaskRequestPayload | dict[str, Any],
    ) -> None:
        """Request another agent to perform a task."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.TASK_REQUEST,
            payload=task_payload,
        )
        await self.bus.send(msg)

    async def _send_runtime_message(
        self,
        recipient: str,
        kind: MessageKind,
        payload: MessagePayloadInput,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> None:
        """Send a runtime message with a normalized payload contract."""
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=kind,
            payload=payload,
            correlation_id=correlation_id if correlation_id is not None else "auto",
            causation_id=causation_id,
        )
        await self.bus.send(msg)

    async def request_handoff(
        self,
        recipient: str,
        payload: dict[str, Any],
        *,
        correlation_id: str = "auto",
        causation_id: str | None = None,
    ) -> None:
        """Send a handoff request through the runtime hook surface."""
        await self._emit_handoff(
            recipient=recipient,
            payload=payload,
            correlation_id=None if correlation_id == "auto" else correlation_id,
            causation_id=causation_id,
        )
        msg = new_message(
            sender=self.agent_id,
            recipient=recipient,
            kind=MessageKind.HANDOFF_REQUEST,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        await self.bus.send(msg)

    async def emit_heartbeat(self) -> None:
        """Emit a heartbeat message to the supervisor."""
        msg = new_message(
            sender=self.agent_id,
            recipient="supervisor",
            kind=MessageKind.HEARTBEAT,
            payload={
                "status": self.state.status.value,
                "errors": self.state.error_count,
                "messages_processed": self.state.total_messages_processed,
                "ts": time.time(),
            },
        )
        await self.bus.send(msg)

    # ── Middleware helpers ───────────────────────────────────────

    async def _emit_before_step(
        self,
        *,
        step_kind: str,
        message: AgentMessage | None,
    ) -> None:
        for middleware in self.middlewares:
            await middleware.before_step(self, step_kind=step_kind, message=message)

    async def _emit_after_step(
        self,
        *,
        step_kind: str,
        message: AgentMessage | None,
        error: str | None = None,
    ) -> None:
        for middleware in self.middlewares:
            await middleware.after_step(
                self,
                step_kind=step_kind,
                message=message,
                error=error,
            )

    async def _emit_tool_call(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        for middleware in self.middlewares:
            await middleware.on_tool_call(
                self,
                tool_name=tool_name,
                arguments=arguments,
            )

    async def _emit_tool_result(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any = None,
        error: str | None = None,
    ) -> None:
        for middleware in self.middlewares:
            await middleware.on_tool_result(
                self,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                error=error,
            )

    async def _emit_handoff(
        self,
        *,
        recipient: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None,
    ) -> None:
        for middleware in self.middlewares:
            await middleware.on_handoff(
                self,
                recipient=recipient,
                payload=payload,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )

    async def _emit_retry(
        self,
        *,
        error: str,
        message: AgentMessage | None,
        consecutive_errors: int,
    ) -> None:
        for middleware in self.middlewares:
            try:
                await middleware.on_retry(
                    self,
                    error=error,
                    message=message,
                    consecutive_errors=consecutive_errors,
                )
            except Exception as hook_exc:  # noqa: BLE001
                logger.warning(
                    "[%s] Middleware retry hook failed: %s",
                    self.agent_id,
                    hook_exc,
                )
