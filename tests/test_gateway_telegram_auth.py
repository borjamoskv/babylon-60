from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.gateway.adapters.telegram import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_telegram_webhook_requires_configured_secret(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_TELEGRAM_WEBHOOK_SECRET", raising=False)
    client = _client()

    response = client.post("/gateway/telegram/webhook", json={"message": {}})

    assert response.status_code == 503
    assert response.json()["detail"] == "Telegram webhook secret not configured"


def test_telegram_webhook_rejects_invalid_secret(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_TELEGRAM_WEBHOOK_SECRET", "shared-secret")
    client = _client()

    response = client.post(
        "/gateway/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        json={"message": {}},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid webhook secret"


def test_telegram_webhook_accepts_valid_secret(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_TELEGRAM_WEBHOOK_SECRET", "shared-secret")
    client = _client()

    response = client.post(
        "/gateway/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "shared-secret"},
        json={"message": {}},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_telegram_webhook_blocks_unlisted_chat(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_TELEGRAM_WEBHOOK_SECRET", "shared-secret")
    monkeypatch.setenv("CORTEX_TELEGRAM_CHAT_ID", "42")
    client = _client()

    response = client.post(
        "/gateway/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "shared-secret"},
        json={"message": {"chat": {"id": "24"}, "text": "/status", "from": {"id": "7"}}},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Chat not allowed"


def test_telegram_webhook_accepts_listed_chat(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_TELEGRAM_WEBHOOK_SECRET", "shared-secret")
    monkeypatch.setenv("CORTEX_TELEGRAM_CHAT_ID", "42")
    client = _client()

    response = client.post(
        "/gateway/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "shared-secret"},
        json={"message": {"chat": {"id": "42"}}},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
