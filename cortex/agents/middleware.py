"""CORTEX Agent Runtime — Middleware Hooks.

Opt-in middleware for observing and governing agent runtime steps
without coupling directly to engine persistence or routes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.agents.base import BaseAgent
    from cortex.agents.message_schema import AgentMessage

__all__ = ["AgentMiddleware"]


class AgentMiddleware:
    """Async hook surface for runtime instrumentation and policy layers."""

    async def before_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
    ) -> None:
        """Called before a message or tick step is executed."""

    async def after_step(
        self,
        agent: BaseAgent,
        *,
        step_kind: str,
        message: AgentMessage | None = None,
        error: str | None = None,
    ) -> None:
        """Called after a message or tick step completes."""

    async def on_tool_call(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> None:
        """Called immediately before a tool is executed."""

    async def on_tool_result(
        self,
        agent: BaseAgent,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Called after a tool returns or raises."""

    async def on_handoff(
        self,
        agent: BaseAgent,
        *,
        recipient: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> None:
        """Called before a handoff request is published."""

    async def on_retry(
        self,
        agent: BaseAgent,
        *,
        error: str,
        message: AgentMessage | None = None,
        consecutive_errors: int,
    ) -> None:
        """Called when the runtime records an error and will retry or quarantine."""
