# [C5-REAL] SignalBus — L1 Persistence Bridge
# Implements the _signal_bus slot defined in cortex/events/bus.py
# Every publish() call on DistributedEventBus persists here:
#   append-only SQLite + SHA-256 hash chain + optional HMAC-SHA256

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("cortex.events.signal_bus")

# ---------------------------------------------------------------------------
# Canonical serialization  (deterministic hash input)
# ---------------------------------------------------------------------------

def canonical_json(data: Any) -> bytes:
    """Sort keys recursively, no spaces — stable across Python versions."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(secret: bytes, data: bytes) -> str:
    return _hmac.new(secret, data, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Integrity envelope
# ---------------------------------------------------------------------------

def build_integrity(
    previous_hash: Optional[str],
    content: dict,
    hmac_secret: Optional[bytes] = None,
) -> dict:
    """
    Returns integrity block:
      previous_hash  : hash of previous event in stream (None for S0)
      content_hash   : SHA-256 of canonical_json(content)
      chain_hash     : SHA-256(previous_hash + ":" + content_hash)
      hmac_hash      : HMAC-SHA256(secret, chain_material)  — optional
      algorithm      : descriptor string
    """
    content_hash = sha256_hex(canonical_json(content))
    prev = previous_hash or "0" * 64
    chain_material = f"{prev}:{content_hash}".encode()
    chain_hash = sha256_hex(chain_material)

    integrity: dict = {
        "previous_hash": previous_hash,
        "content_hash": content_hash,
        "chain_hash": chain_hash,
        "algorithm": "sha256-chain",
    }
    if hmac_secret:
        integrity["hmac_hash"] = hmac_sha256_hex(hmac_secret, chain_material)
        integrity["algorithm"] = "sha256-chain+hmac-sha256"

    return integrity


# ---------------------------------------------------------------------------
# Event types — domain taxonomy for CORTEX PERSIST
# ---------------------------------------------------------------------------

EVENT_TYPES = {
    # lifecycle
    "SESSION_STARTED", "SESSION_RESUMED", "SESSION_TERMINATED",
    # directive
    "DIRECTIVE_LOADED", "DIRECTIVE_OVERRIDDEN", "CONSTRAINT_REGISTERED",
    # memory
    "MEMORY_BOUND", "MEMORY_INVALIDATED", "CONTEXT_SNAPSHOT_TAKEN",
    # reasoning
    "INTENT_PARSED", "PLAN_GENERATED", "PLAN_REVISED", "REASONING_RECORDED",
    # execution
    "TASK_DISPATCHED", "TASK_COMPLETED", "TASK_FAILED", "TASK_RETRIED",
    # tools
    "TOOL_INVOKED", "TOOL_RESULT_CAPTURED", "TOOL_RESULT_REJECTED",
    # output
    "RESPONSE_GENERATED", "RESPONSE_REVISED",
    # integrity
    "CHAIN_VERIFIED", "ANOMALY_DETECTED", "EXERGY_MEASURED",
}


# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS cortex_events (
    global_position INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_id       TEXT    NOT NULL,
    sequence        INTEGER NOT NULL,
    event_id        TEXT    NOT NULL UNIQUE,
    event_type      TEXT    NOT NULL,
    payload         TEXT    NOT NULL,
    previous_hash   TEXT,
    content_hash    TEXT    NOT NULL,
    chain_hash      TEXT    NOT NULL,
    hmac_hash       TEXT,
    algorithm       TEXT    NOT NULL,
    created_at      REAL    NOT NULL,
    UNIQUE (stream_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_stream ON cortex_events (stream_id, sequence);
"""


# ---------------------------------------------------------------------------
# SignalBus
# ---------------------------------------------------------------------------

@dataclass
class SignalBus:
    """
    L1 Persistence Bridge for DistributedEventBus.

    Usage:
        bus = DistributedEventBus()
        signal_bus = SignalBus(db_path="cortex.db")
        bus.attach_signal_bus(signal_bus)
        # From here: every bus.publish() also persists to SQLite with hash chain.

    Verification:
        SignalBus.verify_chain(db_path="cortex.db", stream_id="cortex/session/xyz")
    """

    db_path: str = "cortex_signals.db"
    hmac_secret: Optional[bytes] = field(default=None, repr=False)
    _conn: Optional[sqlite3.Connection] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        logger.info("SignalBus initialized — db: %s", self.db_path)

    # ------------------------------------------------------------------
    # Public API (matches slot expected by DistributedEventBus.publish)
    # ------------------------------------------------------------------

    def emit(
        self,
        event_type: str,
        payload: dict,
        source: str = "event-bus",
        project: Optional[str] = None,
    ) -> str:
        """
        Append event to SQLite with hash chain.
        Returns chain_hash of persisted event.
        """
        assert self._conn is not None

        stream_id = f"cortex/{project or 'default'}/{source}"
        event_id = f"evt_{uuid.uuid4().hex}"

        with self._conn:
            # Optimistic sequence + previous_hash fetch
            row = self._conn.execute(
                "SELECT sequence, chain_hash FROM cortex_events "
                "WHERE stream_id = ? ORDER BY sequence DESC LIMIT 1",
                (stream_id,),
            ).fetchone()
            sequence = (row[0] + 1) if row else 0
            previous_hash = row[1] if row else None

            content = {
                "event_id": event_id,
                "stream_id": stream_id,
                "sequence": sequence,
                "event_type": event_type,
                "payload": payload,
            }
            integrity = build_integrity(previous_hash, content, self.hmac_secret)

            self._conn.execute(
                """
                INSERT INTO cortex_events
                    (stream_id, sequence, event_id, event_type, payload,
                     previous_hash, content_hash, chain_hash, hmac_hash,
                     algorithm, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    stream_id,
                    sequence,
                    event_id,
                    event_type,
                    canonical_json(payload).decode(),
                    integrity["previous_hash"],
                    integrity["content_hash"],
                    integrity["chain_hash"],
                    integrity.get("hmac_hash"),
                    integrity["algorithm"],
                    time.time(),
                ),
            )

        logger.debug(
            "[%s] seq=%d chain=%s",
            stream_id, sequence, integrity["chain_hash"][:16],
        )
        return integrity["chain_hash"]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # External verification (runs independently of the bus)
    # ------------------------------------------------------------------

    @staticmethod
    def verify_chain(
        db_path: str,
        stream_id: str,
        hmac_secret: Optional[bytes] = None,
    ) -> dict:
        """
        Independently verifies the hash chain for a stream.
        Returns:
          {"valid": bool, "events_checked": int, "broken_at_sequence": int|None}
        """
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT sequence, event_id, event_type, payload, "
            "previous_hash, content_hash, chain_hash, hmac_hash, algorithm "
            "FROM cortex_events WHERE stream_id = ? ORDER BY sequence ASC",
            (stream_id,),
        ).fetchall()
        conn.close()

        if not rows:
            return {"valid": True, "events_checked": 0, "broken_at_sequence": None}

        expected_previous: Optional[str] = None

        for row in rows:
            seq, event_id, event_type, payload_str, prev_hash, content_hash, chain_hash, hmac_hash, algorithm = row

            # Recompute content_hash
            content = {
                "event_id": event_id,
                "stream_id": stream_id,
                "sequence": seq,
                "event_type": event_type,
                "payload": json.loads(payload_str),
            }
            expected_content_hash = sha256_hex(canonical_json(content))
            if expected_content_hash != content_hash:
                return {"valid": False, "events_checked": seq, "broken_at_sequence": seq,
                        "reason": "content_hash_mismatch"}

            # Recompute chain_hash
            prev = expected_previous or "0" * 64
            chain_material = f"{prev}:{content_hash}".encode()
            expected_chain_hash = sha256_hex(chain_material)
            if expected_chain_hash != chain_hash:
                return {"valid": False, "events_checked": seq, "broken_at_sequence": seq,
                        "reason": "chain_hash_mismatch"}

            # Recompute HMAC if present
            if hmac_secret and hmac_hash:
                expected_hmac = hmac_sha256_hex(hmac_secret, chain_material)
                if expected_hmac != hmac_hash:
                    return {"valid": False, "events_checked": seq, "broken_at_sequence": seq,
                            "reason": "hmac_mismatch"}

            # Previous hash continuity
            if prev_hash != expected_previous:
                return {"valid": False, "events_checked": seq, "broken_at_sequence": seq,
                        "reason": "previous_hash_discontinuity"}

            expected_previous = chain_hash

        return {"valid": True, "events_checked": len(rows), "broken_at_sequence": None}
