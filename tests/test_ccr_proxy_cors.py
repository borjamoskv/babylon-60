from __future__ import annotations

from cortex.extensions.daemon.ccr_proxy import _cors_options, _parse_cors_origins


def test_ccr_proxy_defaults_to_loopback_origins(monkeypatch) -> None:
    monkeypatch.delenv("CCR_ALLOWED_ORIGINS", raising=False)

    assert _parse_cors_origins() == ["http://localhost", "http://127.0.0.1"]
    assert _cors_options()["allow_credentials"] is True


def test_ccr_proxy_wildcard_disables_credentials(monkeypatch) -> None:
    monkeypatch.setenv("CCR_ALLOWED_ORIGINS", "*")

    assert _parse_cors_origins() == ["*"]
    assert _cors_options()["allow_credentials"] is False
