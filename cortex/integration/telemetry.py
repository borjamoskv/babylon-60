from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Awaitable


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_file_hash(path: Path) -> str:
    return _sha256_bytes(path.read_bytes()) if path.exists() else _sha256_bytes(b"")


def compute_agent_fingerprint(
    agent_id: str,
    modules_dir: Path,
    schema_paths: list[Path],
    capability_manifest: dict[str, Any],
) -> str:
    parts: list[str] = [f"agent_id:{agent_id}"]

    if modules_dir.exists():
        for p in sorted([x for x in modules_dir.rglob("*") if x.is_file()]):
            parts.append(f"module:{p.as_posix()}:{_read_file_hash(p)}")

    for schema_path in schema_paths:
        parts.append(f"schema:{schema_path.as_posix()}:{_read_file_hash(schema_path)}")

    cap_json = json.dumps(capability_manifest, sort_keys=True, separators=(",", ":")).encode()
    parts.append(f"caps:{_sha256_bytes(cap_json)}")

    return _sha256_bytes("\n".join(parts).encode())


@dataclass(frozen=True)
class TelemetryEvent:
    agent_id: str
    fingerprint: str
    timestamp: float
    capabilities: dict[str, Any]
    schema_version: str


class AgentTelemetryEmitter:
    def __init__(
        self,
        agent_id: str,
        modules_dir: Path,
        schema_paths: list[Path],
        capability_manifest: dict[str, Any],
        publish: Callable[[dict[str, Any]], Awaitable[None]],
        interval_s: float = 5.0,
    ):
        self.agent_id = agent_id
        self.modules_dir = modules_dir
        self.schema_paths = schema_paths
        self.capability_manifest = capability_manifest
        self.publish = publish
        self.interval_s = interval_s
        self.running = False

    async def emit_once(self) -> TelemetryEvent:
        fp = compute_agent_fingerprint(
            self.agent_id,
            self.modules_dir,
            self.schema_paths,
            self.capability_manifest,
        )
        event = TelemetryEvent(
            agent_id=self.agent_id,
            fingerprint=fp,
            timestamp=time.time(),
            capabilities=self.capability_manifest,
            schema_version=str(self.capability_manifest.get("schema_version", "unknown")),
        )
        await self.publish(asdict(event))
        return event

    async def run(self) -> None:
        self.running = True
        while self.running:
            await self.emit_once()
            await asyncio.sleep(self.interval_s)

    def stop(self) -> None:
        self.running = False
