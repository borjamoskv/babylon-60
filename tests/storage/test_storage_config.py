from __future__ import annotations

import pytest

from cortex.storage import StorageMode, get_storage_config, get_storage_mode


@pytest.fixture(autouse=True)
def clean_storage_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "CORTEX_STORAGE",
        "TURSO_DATABASE_URL",
        "TURSO_AUTH_TOKEN",
        "POSTGRES_DSN",
    ):
        monkeypatch.delenv(key, raising=False)


def test_storage_mode_defaults_to_local() -> None:
    assert get_storage_mode() is StorageMode.LOCAL
    assert get_storage_config() == {"mode": StorageMode.LOCAL}


def test_storage_mode_falls_back_to_local_for_unknown_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "unknown")

    assert get_storage_mode() is StorageMode.LOCAL


def test_turso_config_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "turso")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")

    with pytest.raises(ValueError, match="TURSO_DATABASE_URL is required"):
        get_storage_config()


def test_turso_config_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "turso")
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://db.example")

    with pytest.raises(ValueError, match="TURSO_AUTH_TOKEN is required"):
        get_storage_config()


def test_turso_config_includes_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "turso")
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://db.example")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "token")

    assert get_storage_config() == {
        "mode": StorageMode.TURSO,
        "url": "libsql://db.example",
        "token": "token",
    }


def test_postgres_config_requires_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "postgres")

    with pytest.raises(ValueError, match="POSTGRES_DSN is required"):
        get_storage_config()


def test_postgres_config_includes_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_STORAGE", "postgres")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://user:pass@localhost/cortex")

    assert get_storage_config() == {
        "mode": StorageMode.POSTGRES,
        "dsn": "postgresql://user:pass@localhost/cortex",
    }
