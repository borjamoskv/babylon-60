"""connector_agent.py — ConnectorAgent (BaseAgent)

Daemon agent that runs connector ingest cycles on a configurable interval.
Responds to TASK_REQUEST for on-demand pulls.

Bus OPs:
    {"op": "pull"}              → run single ingest cycle immediately
    {"op": "status"}            → return last ingest result summary
    {"op": "connect"}           → (re)authenticate connector
    {"op": "disconnect"}        → close connector session

Emits ALERT_ENTROPY if ingest errors exceed threshold.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import SqliteMessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.extensions.connectors.base import BaseConnector, IngestResult

logger = logging.getLogger(__name__)

_SUPPORTED_OPS: frozenset[str] = frozenset({"pull", "status", "connect", "disconnect"})


class ConnectorAgent(BaseAgent):
    """Daemon agent — runs BaseConnector.ingest() on a polling interval.

    Config:
        manifest.daemon = True
        connector.config.poll_interval_seconds → how often to auto-pull
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: SqliteMessageBus,
        tool_registry: ToolRegistry,
        connector: BaseConnector,
        error_alert_threshold: int = 5,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._connector = connector
        self._error_threshold = error_alert_threshold
        self._last_result: IngestResult | None = None
        self._last_pull_ts: float = 0.0
        self._connected: bool = False

    # ── Daemon tick ───────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        """Connect on agent start."""
        try:
            await self._connector.connect()
            self._connected = True
            logger.info(
                "[ConnectorAgent:%s] connected → %s",
                self.agent_id, self._connector.connector_id,
            )
        except Exception as exc:
            logger.error("[ConnectorAgent:%s] connect() failed: %s", self.agent_id, exc)
            self._connected = False

    async def on_stop(self) -> None:
        """Disconnect on agent stop."""
        if self._connected:
            try:
                await self._connector.disconnect()
            except Exception as exc:
                logger.warning("[ConnectorAgent:%s] disconnect() error: %s", self.agent_id, exc)
            self._connected = False

    async def tick(self) -> None:
        """Auto-pull on interval if connected."""
        if not self._connected:
            return

        interval = self._connector.config.poll_interval_seconds
        now = time.time()
        if now - self._last_pull_ts < interval:
            return

        await self._run_ingest()

    # ── Message handler ───────────────────────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op = payload.get("op", "")

        if op not in _SUPPORTED_OPS:
            await self._reply(message, {
                "error": f"unsupported op: {op!r}",
                "supported": sorted(_SUPPORTED_OPS),
            })
            return

        try:
            result = await self._dispatch(op)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("[ConnectorAgent:%s] op=%s failed", self.agent_id, op)
            await self._reply(message, {"op": op, "error": str(exc)})

    async def _dispatch(self, op: str) -> Any:
        if op == "pull":
            result = await self._run_ingest()
            return str(result)
        if op == "status":
            lr = self._last_result
            return {
                "connected": self._connected,
                "last_pull_ts": self._last_pull_ts,
                "last_result": str(lr) if lr else None,
                "connector_id": self._connector.connector_id,
            }
        if op == "connect":
            await self._connector.connect()
            self._connected = True
            return {"connected": True}
        if op == "disconnect":
            await self._connector.disconnect()
            self._connected = False
            return {"connected": False}
        raise ValueError(f"unknown op: {op!r}")

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _run_ingest(self) -> IngestResult:
        logger.info("[ConnectorAgent:%s] starting ingest", self.agent_id)
        result = await self._connector.ingest()
        self._last_result = result
        self._last_pull_ts = time.time()

        if len(result.errors) >= self._error_threshold:
            await self._emit_alert(result)

        return result

    async def _emit_alert(self, result: IngestResult) -> None:
        targets = self.manifest.escalation_targets or []
        if not targets:
            return
        for target in targets:
            msg = new_message(
                sender=self.manifest.agent_id,
                recipient=target,
                kind=MessageKind.ALERT_ENTROPY,
                payload={
                    "source": "connector_agent",
                    "connector_id": result.connector_id,
                    "severity": "high",
                    "description": (
                        f"Connector '{result.connector_id}' ingest: "
                        f"{len(result.errors)} errors in {result.records_fetched} records. "
                        f"Errors: {result.errors[:3]}"
                    ),
                },
            )
            await self.bus.send(msg)

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
