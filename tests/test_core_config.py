from __future__ import annotations

from cortex.core.config import DEFAULT_DB_PATH, CortexConfig


def test_from_env_prefers_cortex_db_path(monkeypatch, tmp_path) -> None:
    explicit = tmp_path / "explicit.db"
    fallback = tmp_path / "fallback.db"
    monkeypatch.setenv("CORTEX_DB_PATH", str(explicit))
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    cfg = CortexConfig.from_env()

    assert cfg.DB_PATH == str(explicit)


def test_from_env_falls_back_to_cortex_db(monkeypatch, tmp_path) -> None:
    fallback = tmp_path / "fallback.db"
    monkeypatch.delenv("CORTEX_DB_PATH", raising=False)
    monkeypatch.setenv("CORTEX_DB", str(fallback))

    cfg = CortexConfig.from_env()

    assert cfg.DB_PATH == str(fallback)


def test_from_env_uses_default_when_no_db_env_is_set(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_DB_PATH", raising=False)
    monkeypatch.delenv("CORTEX_DB", raising=False)

    cfg = CortexConfig.from_env()

    assert cfg.DB_PATH == str(DEFAULT_DB_PATH)
