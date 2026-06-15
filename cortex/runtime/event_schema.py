# [C5-REAL] Exergy-Maximized
"""Event Trace Schema — Canonical format for serialized event traces.

This module defines the JSON schema for event traces and provides
serialization/deserialization utilities. This is the formal contract
for any trace that enters the replay engine.

Schema version: 1.0
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cortex.runtime.system_state import StateEvent, SystemStateVector

# ═══════════════════════════════════════════════════════════════════
# JSON SCHEMA (v1.0)
# ═══════════════════════════════════════════════════════════════════

EVENT_SCHEMA_VERSION = "1.0"

EVENT_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CORTEX Event Trace",
    "description": "Canonical format for serialized causal event traces.",
    "type": "object",
    "required": ["version", "trace_id", "events", "metadata"],
    "properties": {
        "version": {
            "type": "string",
            "const": EVENT_SCHEMA_VERSION,
            "description": "Schema version. Must be '1.0'.",
        },
        "trace_id": {
            "type": "string",
            "description": "Unique identifier for this trace (SHA-256 of serialized events).",
        },
        "events": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["tick", "timestamp", "event_type", "source", "prev_hash", "hash"],
                "properties": {
                    "tick": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Monotonic event counter.",
                    },
                    "timestamp": {
                        "type": "number",
                        "description": "Monotonic timestamp (seconds).",
                    },
                    "event_type": {
                        "type": "string",
                        "pattern": r"^[a-z]+\.[a-z_]+$",
                        "description": "Dot-separated event type (e.g. 'agent.started').",
                    },
                    "source": {
                        "type": "string",
                        "description": "Origin of the event (agent_id or 'system').",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Arbitrary event payload.",
                        "default": {},
                    },
                    "prev_hash": {
                        "type": "string",
                        "minLength": 64,
                        "maxLength": 64,
                        "description": "SHA-256 hash of the previous state.",
                    },
                    "hash": {
                        "type": "string",
                        "minLength": 64,
                        "maxLength": 64,
                        "description": "SHA-256 hash of this event.",
                    },
                },
                "additionalProperties": False,
            },
        },
        "metadata": {
            "type": "object",
            "required": ["genesis_hash", "final_hash", "total_ticks"],
            "properties": {
                "genesis_hash": {
                    "type": "string",
                    "description": "Hash of the genesis state.",
                },
                "final_hash": {
                    "type": "string",
                    "description": "Hash after all events applied.",
                },
                "total_ticks": {
                    "type": "integer",
                    "description": "Total number of ticks in the trace.",
                },
                "source_tag": {
                    "type": "string",
                    "description": "Git tag or checkpoint that produced this trace.",
                },
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
}


# ═══════════════════════════════════════════════════════════════════
# SERIALIZATION
# ═══════════════════════════════════════════════════════════════════


def event_to_dict(event: StateEvent) -> dict[str, Any]:
    """Serialize a StateEvent to a schema-compliant dict."""
    return {
        "tick": event.tick,
        "timestamp": event.timestamp,
        "event_type": event.event_type,
        "source": event.source,
        "payload": event.payload,
        "prev_hash": event.prev_hash,
        "hash": event.hash,
    }


def dict_to_event(data: dict[str, Any]) -> StateEvent:
    """Deserialize a dict to a StateEvent."""
    return StateEvent(
        tick=data["tick"],
        timestamp=data["timestamp"],
        event_type=data["event_type"],
        source=data["source"],
        payload=data.get("payload", {}),
        prev_hash=data["prev_hash"],
        hash=data["hash"],
    )


def compute_trace_id(events: list[dict[str, Any]]) -> str:
    """Compute a deterministic trace ID from serialized events."""
    blob = json.dumps(
        [{"tick": e["tick"], "type": e["event_type"], "hash": e["hash"]} for e in events],
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def serialize_trace(
    sv: SystemStateVector,
    source_tag: str = "",
) -> dict[str, Any]:
    """Serialize a SystemStateVector's ledger to the canonical trace format.

    Args:
        sv: The state vector whose ledger to serialize.
        source_tag: Optional git tag / checkpoint identifier.

    Returns:
        A dict conforming to EVENT_JSON_SCHEMA.
    """
    events = [event_to_dict(e) for e in sv._ledger]
    trace_id = compute_trace_id(events)

    return {
        "version": EVENT_SCHEMA_VERSION,
        "trace_id": trace_id,
        "events": events,
        "metadata": {
            "genesis_hash": sv._genesis_hash(),
            "final_hash": sv.hash,
            "total_ticks": sv.tick,
            "source_tag": source_tag,
        },
    }


def deserialize_trace(data: dict[str, Any]) -> list[StateEvent]:
    """Deserialize a trace dict to a list of StateEvents.

    Args:
        data: A dict conforming to EVENT_JSON_SCHEMA.

    Returns:
        List of StateEvent objects.

    Raises:
        ValueError: If version mismatch or structural errors.
    """
    version = data.get("version", "")
    if version != EVENT_SCHEMA_VERSION:
        raise ValueError(f"Schema version mismatch: expected {EVENT_SCHEMA_VERSION}, got {version}")

    events_raw = data.get("events", [])
    if not events_raw:
        raise ValueError("Trace contains no events")

    return [dict_to_event(e) for e in events_raw]


def save_trace(sv: SystemStateVector, path: Path | str, source_tag: str = "") -> Path:
    """Serialize and save a trace to a JSON file.

    Args:
        sv: The state vector whose ledger to save.
        path: File path for the output JSON.
        source_tag: Optional git tag / checkpoint identifier.

    Returns:
        The Path of the saved file.
    """
    path = Path(path)
    trace = serialize_trace(sv, source_tag=source_tag)
    path.write_text(json.dumps(trace, indent=2, sort_keys=False))
    return path


def load_trace(path: Path | str) -> list[StateEvent]:
    """Load and deserialize a trace from a JSON file.

    Args:
        path: Path to the trace JSON file.

    Returns:
        List of StateEvent objects.
    """
    path = Path(path)
    data = json.loads(path.read_text())
    return deserialize_trace(data)
