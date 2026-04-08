"""
tempus_fugit_agent.py — TempusFugitAgent

Reactive temporal agent wrapping TimingTracker plus timestamp normalization
helpers so callers can work with activity time, summaries, and timelines
through the agent message bus.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry
from cortex.extensions.timing.tracker import TimingTracker
from cortex.memory.temporal import normalize_timestamp, now_iso

logger = logging.getLogger(__name__)

_SUPPORTED_OPS: frozenset[str] = frozenset(
    {"heartbeat", "flush", "today", "report", "timeline", "daily", "normalize", "now", "status"}
)


class TempusFugitAgent(BaseAgent):
    """Reactive agent for activity tracking and temporal queries."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry,
        tracker: TimingTracker,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._tracker = tracker

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op = str(payload.get("op", ""))

        if op not in _SUPPORTED_OPS:
            await self._reply(
                message,
                {"error": f"unsupported op: {op!r}", "supported": sorted(_SUPPORTED_OPS)},
            )
            return

        try:
            result = self._dispatch(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except Exception as exc:
            logger.exception("TempusFugitAgent op=%s failed", op)
            await self._reply(message, {"op": op, "error": str(exc)})

    async def tick(self) -> None:
        logger.debug("TempusFugitAgent tick — idle")

    def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "heartbeat":
            heartbeat_id = self._tracker.heartbeat(
                project=_required_str(payload, "project"),
                entity=str(payload.get("entity", "")),
                category=_optional_str(payload.get("category")),
                branch=_optional_str(payload.get("branch")),
                language=_optional_str(payload.get("language")),
                timestamp=_normalize_payload_timestamp(payload.get("timestamp")),
                meta=_optional_dict(payload.get("meta")),
            )
            return {"heartbeat_id": heartbeat_id}

        if op == "flush":
            return {"entries_created": self._tracker.flush(_optional_int(payload.get("gap_seconds")))}

        if op == "today":
            return _summary_to_dict(self._tracker.today(project=_optional_str(payload.get("project"))))

        if op == "report":
            return _summary_to_dict(
                self._tracker.report(
                    project=_optional_str(payload.get("project")),
                    days=int(payload.get("days", 7)),
                )
            )

        if op == "timeline":
            entries = self._tracker.timeline(
                project=_optional_str(payload.get("project")),
                date=_optional_str(payload.get("date")),
            )
            return [_time_entry_to_dict(entry) for entry in entries]

        if op == "daily":
            return self._tracker.daily(days=int(payload.get("days", 7)))

        if op == "normalize":
            return {"value": _normalize_payload_timestamp(payload.get("value"))}

        if op == "now":
            return {"value": now_iso()}

        if op == "status":
            return {
                "agent": self.manifest.agent_id,
                "status": "ok",
                "supported_ops": sorted(_SUPPORTED_OPS),
            }

        raise ValueError(f"unknown op: {op!r}")

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)


def _summary_to_dict(summary: Any) -> dict[str, Any]:
    data = asdict(summary)
    data["total_hours"] = summary.total_hours
    return data


def _time_entry_to_dict(entry: Any) -> dict[str, Any]:
    return asdict(entry)


def _normalize_payload_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            if len(value) == 10:
                return normalize_timestamp(date.fromisoformat(value))
            return normalize_timestamp(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return value
    return normalize_timestamp(value)


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("meta must be an object")
    return value


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None or value == "":
        raise ValueError(f"{key} is required")
    return str(value)
