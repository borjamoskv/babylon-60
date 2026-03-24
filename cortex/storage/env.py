"""Cloud/storage environment helpers with backwards-compatible aliases."""

from __future__ import annotations

import os
from collections.abc import Iterable

__all__ = [
    "get_postgres_dsn",
    "get_qdrant_api_key",
    "get_qdrant_url",
    "get_redis_url",
    "get_turso_url",
    "get_turso_auth_token",
]


def _first_non_empty(keys: Iterable[str]) -> str:
    """Return the first non-empty environment value for the given keys."""
    for key in keys:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def get_postgres_dsn() -> str | None:
    """Resolve PostgreSQL DSN from supported aliases."""
    value = _first_non_empty(
        ("POSTGRES_DSN", "CORTEX_PG_DSN", "CORTEX_PG_URL", "DATABASE_URL", "PG_URL")
    )
    return value or None


def get_qdrant_url(default: str = "http://localhost:6333") -> str:
    """Resolve Qdrant URL from supported aliases."""
    return _first_non_empty(("QDRANT_URL", "CORTEX_QDRANT_URL")) or default


def get_qdrant_api_key() -> str | None:
    """Resolve optional Qdrant API key from supported aliases."""
    value = _first_non_empty(("QDRANT_API_KEY", "CORTEX_QDRANT_API_KEY"))
    return value or None


def get_redis_url(default: str = "redis://localhost:6379/0") -> str:
    """Resolve Redis URL from supported aliases."""
    return _first_non_empty(("REDIS_URL", "CORTEX_REDIS_URL")) or default


def get_turso_url() -> str | None:
    """Resolve Turso/libSQL database URL."""
    value = _first_non_empty(
        ("TURSO_DATABASE_URL", "LIBSQL_URL", "CORTEX_TURSO_URL", "CORTEX_STORAGE_URL")
    )
    return value or None


def get_turso_auth_token() -> str | None:
    """Resolve Turso/libSQL auth token."""
    value = _first_non_empty(
        ("TURSO_AUTH_TOKEN", "LIBSQL_AUTH_TOKEN", "CORTEX_TURSO_TOKEN", "CORTEX_STORAGE_TOKEN")
    )
    return value or None
