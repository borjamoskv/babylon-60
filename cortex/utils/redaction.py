"""Redaction helpers for telemetry, logs, and audit-adjacent payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Final

__all__ = ["REDACTED", "redact_mapping", "redact_text", "redact_value"]

REDACTED: Final = "[REDACTED]"

_REDACTED_TOKEN: Final = "[REDACTED_TOKEN]"
_REDACTED_EMAIL: Final = "[REDACTED_EMAIL]"
_REDACTED_NUMBER: Final = "[REDACTED_NUMBER]"
_REDACTED_PATH: Final = "[REDACTED_PATH]"
_REDACTED_PRIVATE_KEY: Final = "[REDACTED_PRIVATE_KEY]"

_PRIVATE_KEY_RE: Final = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]{0,4096}?-----END [A-Z0-9 ]*PRIVATE KEY-----",
)
_JWT_RE: Final = re.compile(
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
)
_BEARER_RE: Final = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE)
_CORTEX_KEY_RE: Final = re.compile(r"\bctx_[A-Za-z0-9_=-]{8,}\b")
_SECRET_ASSIGNMENT_RE: Final = re.compile(
    r"(?P<key>\b(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"id[_-]?token|token|secret|password|passwd|cookie|set-cookie|session[_-]?id|"
    r"private[_-]?key)\b)(?P<sep>\s*[:=]\s*)(?P<value>[\"']?[^\s,;|}]+[\"']?)",
    re.IGNORECASE,
)
_EMAIL_RE: Final = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")
_IBAN_RE: Final = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]{0,16}\b", re.IGNORECASE)
_CARD_RE: Final = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_LOCAL_PATH_RE: Final = re.compile(
    r"(?:/(?:Users|home|var|tmp|private|etc)(?:/[^\s\"'<>|,;:)]+)+)|"
    r"(?:[A-Za-z]:\\[^\s\"'<>|]+)"
)

_SENSITIVE_KEY_PARTS: Final = frozenset(
    {
        "authorization",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "secret",
        "password",
        "passwd",
        "cookie",
        "set_cookie",
        "session",
        "session_id",
        "private_key",
        "tx_id",
        "transaction_id",
        "account",
        "iban",
        "card",
        "dni",
        "nif",
        "ssn",
    }
)


def redact_text(value: str) -> str:
    """Redact high-risk secrets and PII from a single text value."""
    redacted = _PRIVATE_KEY_RE.sub(_REDACTED_PRIVATE_KEY, value)
    redacted = _JWT_RE.sub(_REDACTED_TOKEN, redacted)
    redacted = _BEARER_RE.sub(f"Bearer {_REDACTED_TOKEN}", redacted)
    redacted = _CORTEX_KEY_RE.sub(_REDACTED_TOKEN, redacted)
    redacted = _SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group('key')}{match.group('sep')}{_REDACTED_TOKEN}",
        redacted,
    )
    redacted = _EMAIL_RE.sub(_REDACTED_EMAIL, redacted)
    redacted = _IBAN_RE.sub(_REDACTED_NUMBER, redacted)
    redacted = _CARD_RE.sub(_REDACTED_NUMBER, redacted)
    return _LOCAL_PATH_RE.sub(_REDACTED_PATH, redacted)


def redact_mapping(value: Mapping[Any, Any]) -> dict[Any, Any]:
    """Return a redacted copy of a mapping without mutating the source object."""
    redacted: dict[Any, Any] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            redacted[key] = REDACTED
        else:
            redacted[key] = redact_value(item)
    return redacted


def redact_value(value: Any) -> Any:
    """Recursively redact telemetry/log values while preserving safe scalar types."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, set):
        return {redact_value(item) for item in value}
    return value


def _is_sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
    compact = normalized.replace("_", "")
    return any(
        part == normalized or part in normalized.split("_") or part.replace("_", "") in compact
        for part in _SENSITIVE_KEY_PARTS
    )
