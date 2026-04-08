"""Persistent session wrapper around the GitHubAgent builtin."""

from __future__ import annotations

import time
import uuid
from typing import Any

from cortex.agents.builtins import GitHubAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import MessageKind, new_message
from cortex.agents.supervisor import Supervisor
from cortex.agents.tools import ToolRegistry

__all__ = ["GitHubAgentSession"]


def _make_db_uri() -> str:
    return f"file:github_agent_session_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


class GitHubAgentSession:
    """Manage a live GitHubAgent for repeated request/response interactions."""

    def __init__(
        self,
        *,
        agent_id: str = "cortex-github",
        caller_id: str = "github-session",
        db_path: str | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.caller_id = caller_id
        self.db_path = db_path or _make_db_uri()
        self._bus: SqliteMessageBus | None = None
        self._supervisor: Supervisor | None = None
        self._started = False

    async def __aenter__(self) -> GitHubAgentSession:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        if self._started:
            return

        bus = SqliteMessageBus(db_path=self.db_path)
        manifest = AgentManifest(
            agent_id=self.agent_id,
            purpose="GitHub navigation and gh workflows",
            tools_allowed=[],
            daemon=False,
        )
        agent = GitHubAgent(
            manifest=manifest,
            bus=bus,
            tool_registry=ToolRegistry(),
        )
        supervisor = Supervisor()
        supervisor.register(agent)
        await supervisor.start_agent(self.agent_id)

        self._bus = bus
        self._supervisor = supervisor
        self._started = True

    async def request(self, payload: dict[str, Any], *, timeout: float = 5.0) -> dict[str, Any]:
        if not self._started:
            await self.start()
        if self._bus is None:
            raise RuntimeError("GitHubAgentSession bus is not initialised.")

        await self._bus.send(
            new_message(
                sender=self.caller_id,
                recipient=self.agent_id,
                kind=MessageKind.TASK_REQUEST,
                payload=payload,
            )
        )

        deadline = time.monotonic() + timeout
        reply = None
        while time.monotonic() < deadline:
            reply = await self._bus.receive(self.caller_id, timeout=1.0)
            if reply is not None:
                break

        if reply is None:
            return {"ok": False, "error": "timeout waiting for GitHubAgent reply"}
        return dict(reply.payload)

    async def close(self) -> None:
        supervisor = self._supervisor
        bus = self._bus
        self._supervisor = None
        self._bus = None
        self._started = False

        if supervisor is not None:
            try:
                await supervisor.stop_agent(self.agent_id)
            except Exception:
                pass
        if bus is not None:
            await bus.close()
