"""FL Studio bridge tools for the CORTEX MCP server.

The tools in this module do not talk to FL Studio directly. They invoke a
local bridge command that translates a narrow JSON protocol into the actual
automation layer chosen by the user, such as FL Studio MIDI scripting,
virtual MIDI, or OSC.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("cortex.mcp.fl_studio")

_READ_ACTIONS = frozenset(
    {
        "session.status",
        "transport.status",
        "mixer.channels.list",
    }
)
_WRITE_ACTIONS = frozenset(
    {
        "transport.play",
        "transport.stop",
        "project.tempo.set",
    }
)
_ALL_ACTIONS = _READ_ACTIONS | _WRITE_ACTIONS

_NOT_CONFIGURED = (
    "FL Studio bridge not configured. Set CORTEX_FL_STUDIO_BRIDGE_CMD to a local command, "
    "for example: "
    '"python3 /absolute/path/examples/fl_studio/fl_studio_bridge_stub.py"'
)


class FLStudioBridgeProtocol(Protocol):
    """Runtime contract used by the MCP tool registry."""

    write_enabled: bool

    async def invoke(
        self,
        action: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Execute a bridge action and return the parsed JSON response."""


@dataclass(frozen=True)
class FLStudioBridgeConfig:
    """Configuration for the local FL Studio bridge command."""

    command: tuple[str, ...]
    timeout_seconds: int = 5
    write_enabled: bool = False

    @classmethod
    def from_env(cls) -> FLStudioBridgeConfig | None:
        """Build configuration from environment variables."""
        raw_command = os.getenv("CORTEX_FL_STUDIO_BRIDGE_CMD", "").strip()
        if not raw_command:
            return None

        timeout_raw = os.getenv("CORTEX_FL_STUDIO_BRIDGE_TIMEOUT", "5").strip()
        try:
            timeout_seconds = max(1, int(timeout_raw))
        except ValueError:
            timeout_seconds = 5

        return cls(
            command=tuple(shlex.split(raw_command)),
            timeout_seconds=timeout_seconds,
            write_enabled=os.getenv("CORTEX_FL_STUDIO_WRITE_ENABLE", "0") == "1",
        )


class FLStudioBridgeError(RuntimeError):
    """Raised when the bridge command cannot complete successfully."""


class FLStudioBridgeClient:
    """Thin async JSON-RPC-ish client for a local FL Studio bridge process."""

    def __init__(self, config: FLStudioBridgeConfig) -> None:
        self._config = config
        self.write_enabled = config.write_enabled

    @classmethod
    def from_env(cls) -> FLStudioBridgeClient | None:
        """Instantiate a bridge client from environment variables."""
        config = FLStudioBridgeConfig.from_env()
        if config is None:
            return None
        return cls(config)

    async def invoke(
        self,
        action: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Run the bridge command once and return a parsed JSON response."""
        if action not in _ALL_ACTIONS:
            raise FLStudioBridgeError(f"Unsupported FL Studio action: {action}")

        if action in _WRITE_ACTIONS and not self.write_enabled:
            raise FLStudioBridgeError(
                "FL Studio write operations are disabled. Set CORTEX_FL_STUDIO_WRITE_ENABLE=1."
            )

        payload = json.dumps({"action": action, "params": dict(params or {})}, ensure_ascii=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                *self._config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise FLStudioBridgeError(
                f"Unable to start FL Studio bridge command: {' '.join(self._config.command)}"
            ) from exc

        stdout: bytes
        stderr: bytes
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(payload.encode("utf-8")),
                timeout=self._config.timeout_seconds,
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise FLStudioBridgeError("FL Studio bridge timed out.") from exc

        if proc.returncode != 0:
            error_text = stderr.decode("utf-8", errors="replace").strip() or "unknown bridge error"
            raise FLStudioBridgeError(error_text)

        try:
            response = json.loads(stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise FLStudioBridgeError("FL Studio bridge returned invalid JSON.") from exc

        if not isinstance(response, dict):
            raise FLStudioBridgeError("FL Studio bridge returned an invalid payload shape.")

        if response.get("ok") is False:
            raise FLStudioBridgeError(str(response.get("message", "bridge rejected request")))

        return response


def _format_bridge_error(exc: Exception) -> str:
    return f"❌ FL Studio bridge error: {exc}"


def _normalize_bpm(bpm: str) -> str:
    try:
        value = Decimal(bpm)
    except InvalidOperation as exc:
        raise ValueError("BPM must be a valid decimal number.") from exc

    if value < Decimal("20") or value > Decimal("300"):
        raise ValueError("BPM must be between 20 and 300.")

    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def register_fl_studio_tools(
    mcp: FastMCP, bridge: FLStudioBridgeProtocol | None = None
) -> None:  # type: ignore[reportInvalidTypeForm]
    """Register a safe FL Studio control surface on the MCP server."""
    client = bridge or FLStudioBridgeClient.from_env()

    @mcp.tool()
    async def fl_studio_status() -> str:
        """Report bridge connectivity and the active FL Studio session."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            response = await client.invoke("session.status")
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio status failed: %s", exc)
            return _format_bridge_error(exc)

        data = response.get("data", {})
        if not isinstance(data, dict):
            data = {}

        return (
            "FL Studio bridge ready\n"
            f"Project: {data.get('project_name', 'unknown')}\n"
            f"Connected: {data.get('connected', True)}\n"
            f"Write enabled: {client.write_enabled}"
        )

    @mcp.tool()
    async def fl_studio_transport_status() -> str:
        """Get the current FL Studio transport state."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            response = await client.invoke("transport.status")
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio transport status failed: %s", exc)
            return _format_bridge_error(exc)

        data = response.get("data", {})
        if not isinstance(data, dict):
            data = {}

        return (
            "FL Studio transport\n"
            f"Playing: {data.get('playing', False)}\n"
            f"Tempo: {data.get('tempo_bpm', 'unknown')} BPM\n"
            f"Song position: {data.get('song_position', 'unknown')}"
        )

    @mcp.tool()
    async def fl_studio_list_channels() -> str:
        """List visible FL Studio channels from the bridge."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            response = await client.invoke("mixer.channels.list")
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio list channels failed: %s", exc)
            return _format_bridge_error(exc)

        data = response.get("data", {})
        channels = data.get("channels", []) if isinstance(data, dict) else []
        if not isinstance(channels, list) or not channels:
            return "FL Studio channels: none reported"

        lines = ["FL Studio channels:"]
        lines.extend(f"- {channel}" for channel in channels)
        return "\n".join(lines)

    @mcp.tool()
    async def fl_studio_play() -> str:
        """Start FL Studio transport playback."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            response = await client.invoke("transport.play")
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio play failed: %s", exc)
            return _format_bridge_error(exc)

        return str(response.get("message", "FL Studio transport started."))

    @mcp.tool()
    async def fl_studio_stop() -> str:
        """Stop FL Studio transport playback."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            response = await client.invoke("transport.stop")
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio stop failed: %s", exc)
            return _format_bridge_error(exc)

        return str(response.get("message", "FL Studio transport stopped."))

    @mcp.tool()
    async def fl_studio_set_tempo(bpm: str) -> str:
        """Set the project tempo in FL Studio."""
        if client is None:
            return _NOT_CONFIGURED

        try:
            normalized_bpm = _normalize_bpm(bpm)
        except ValueError as exc:
            return f"❌ Rejected by Guard: {exc}"

        try:
            response = await client.invoke(
                "project.tempo.set",
                {"tempo_bpm": normalized_bpm},
            )
        except FLStudioBridgeError as exc:
            logger.warning("FL Studio set tempo failed: %s", exc)
            return _format_bridge_error(exc)

        return str(response.get("message", f"FL Studio tempo set to {normalized_bpm} BPM."))
