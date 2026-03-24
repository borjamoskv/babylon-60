"""
CORTEX EPISTEMIC ISOLATION: Storage Environment Aliases
Component: cortex.storage.env
Axiom: Zero state leakage between validation boundaries.
Refinement: 130/100 (Sovereign Epistemic Containment).
"""
from typing import Final

import pytest

from cortex.storage.env import (
    _first_non_empty,
    get_postgres_dsn,
    get_qdrant_api_key,
    get_qdrant_url,
    get_redis_url,
    get_turso_auth_token,
    get_turso_url,
)

# Complete ledger of all environmental vectors affecting storage connection routing
CORTEX_ENV_VECTORS: Final[tuple[str, ...]] = (
    "A", "B", "C",
    "POSTGRES_DSN", "CORTEX_PG_DSN", "CORTEX_PG_URL", "DATABASE_URL", "PG_URL",
    "QDRANT_URL", "CORTEX_QDRANT_URL", "QDRANT_API_KEY", "CORTEX_QDRANT_API_KEY",
    "REDIS_URL", "CORTEX_REDIS_URL",
    "TURSO_DATABASE_URL", "LIBSQL_URL", "CORTEX_TURSO_URL", "CORTEX_STORAGE_URL",
    "TURSO_AUTH_TOKEN", "LIBSQL_AUTH_TOKEN", "CORTEX_TURSO_TOKEN", "CORTEX_STORAGE_TOKEN",
)


@pytest.fixture(autouse=True)
def _epistemic_containment(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Forces an absolute vacuum.
    Guarantees no environmental state leakage carries over between boundary tests.
    """
    for vector in CORTEX_ENV_VECTORS:
        monkeypatch.delenv(vector, raising=False)


@pytest.mark.parametrize(
    "env_var,expected",
    [
        ("TURSO_DATABASE_URL", "libsql://primary.turso.io"),
        ("LIBSQL_URL", "libsql://secondary.turso.io"),
        ("CORTEX_TURSO_URL", "libsql://tertiary.turso.io"),
        ("CORTEX_STORAGE_URL", "libsql://quaternary.turso.io"),
    ],
)
def test_get_turso_aliases(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:

    monkeypatch.setenv(env_var, expected)
    assert get_turso_url() == expected


@pytest.mark.parametrize(
    "env_var,expected",
    [
        ("TURSO_AUTH_TOKEN", "token-primary"),
        ("LIBSQL_AUTH_TOKEN", "token-secondary"),
        ("CORTEX_TURSO_TOKEN", "token-tertiary"),
        ("CORTEX_STORAGE_TOKEN", "token-quaternary"),
    ],
)
def test_get_turso_auth_aliases(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:

    monkeypatch.setenv(env_var, expected)
    assert get_turso_auth_token() == expected


def test_first_non_empty_mechanics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies priority resolution over thermodynamic noise (whitespace)."""
    monkeypatch.setenv("A", "  1  ")
    monkeypatch.setenv("B", "   ")
    monkeypatch.setenv("C", "3")

    assert _first_non_empty(("X", "Y")) == ""
    assert _first_non_empty(("B", "A")) == "1"
    assert _first_non_empty(("A", "C")) == "1"
    assert _first_non_empty(("C", "A")) == "3"


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("POSTGRES_DSN", "postgresql://dsn"),
        ("CORTEX_PG_DSN", "postgresql://cortex-dsn"),
        ("CORTEX_PG_URL", "postgresql://cortex-url"),
        ("DATABASE_URL", "postgresql://db-url"),
        ("PG_URL", "postgresql://pg-url"),
    ],
)
def test_postgres_dsn_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_postgres_dsn() == expected


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("QDRANT_URL", "https://qdrant.example.com"),
        ("CORTEX_QDRANT_URL", "https://cortex.example.com"),
    ],
)
def test_qdrant_url_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_qdrant_url() == expected


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("QDRANT_API_KEY", "secret1"),
        ("CORTEX_QDRANT_API_KEY", "secret2"),
    ],
)
def test_qdrant_api_key_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_qdrant_api_key() == expected


def test_qdrant_defaults() -> None:
    """Verifies fallback states when no vectors are overridden."""
    assert get_qdrant_url() == "http://localhost:6333"
    assert get_qdrant_url(default="custom") == "custom"
    assert get_qdrant_api_key() is None


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("REDIS_URL", "redis://main:6379"),
        ("CORTEX_REDIS_URL", "redis://cortex:6379"),
    ],
)
def test_redis_url_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_redis_url() == expected


def test_redis_defaults() -> None:
    assert get_redis_url() == "redis://localhost:6379/0"


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("TURSO_DATABASE_URL", "libsql://turso-primary"),
        ("LIBSQL_URL", "libsql://libsql-url"),
        ("CORTEX_TURSO_URL", "libsql://cortex-turso"),
        ("CORTEX_STORAGE_URL", "libsql://cortex-storage"),
    ],
)
def test_turso_url_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_turso_url() == expected


@pytest.mark.parametrize(
    ("env_var", "expected"),
    [
        ("TURSO_AUTH_TOKEN", "token-turso"),
        ("LIBSQL_AUTH_TOKEN", "token-libsql"),
        ("CORTEX_TURSO_TOKEN", "token-cortex-turso"),
        ("CORTEX_STORAGE_TOKEN", "token-cortex-storage"),
    ],
)
def test_turso_auth_token_resolution(
    monkeypatch: pytest.MonkeyPatch, env_var: str, expected: str
) -> None:
    monkeypatch.setenv(env_var, expected)
    assert get_turso_auth_token() == expected


def test_postgres_defaults() -> None:
    """No env vector set → DSN resolves to None."""
    assert get_postgres_dsn() is None


def test_turso_url_defaults() -> None:
    """No env vector set → Turso URL resolves to None."""
    assert get_turso_url() is None


def test_turso_auth_token_defaults() -> None:
    """No env vector set → Turso auth token resolves to None."""
    assert get_turso_auth_token() is None
