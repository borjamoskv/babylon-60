"""Deterministic hashing helpers for DORA evidence packs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashing."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def sha256_bytes(data: bytes) -> str:
    """Return a prefixed SHA-256 digest for bytes."""

    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_text(text: str) -> str:
    """Return a prefixed SHA-256 digest for UTF-8 text."""

    return sha256_bytes(text.encode("utf-8"))
