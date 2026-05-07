from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient


def _load_api_index() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "api" / "index.py"
    spec = importlib.util.spec_from_file_location("cortex_vercel_api_index", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load api/index.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


api_index = _load_api_index()


def test_health_endpoint() -> None:
    client = TestClient(api_index.app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"service": "cortex-saas-api", "status": "ok"}


def test_checkout_fails_closed_without_billing_plan(monkeypatch) -> None:
    monkeypatch.delenv("STRIPE_PRICE_TABLE", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    client = TestClient(api_index.app)

    response = client.post("/v1/billing/checkout", json={"plan": "pro"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Billing plan is not configured"


def test_checkout_rejects_unknown_plan(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_PRICE_TABLE", '{"pro":"price_test_pro"}')
    client = TestClient(api_index.app)

    response = client.post("/v1/billing/checkout", json={"plan": "enterprise"})

    assert response.status_code == 422


def test_checkout_sanitizes_untrusted_return_urls(monkeypatch) -> None:
    captured: dict = {}

    def fake_checkout(session_kwargs: dict) -> dict:
        captured.update(session_kwargs)
        return {
            "client_secret": None,
            "session_id": "cs_test_123",
            "url": "https://checkout.example.test/c/pay/cs_test_123",
        }

    monkeypatch.setenv("STRIPE_PRICE_TABLE", '{"pro":"price_test_pro"}')
    monkeypatch.setenv("STRIPE_SECRET_KEY", "test-secret")
    monkeypatch.setattr(api_index, "_create_billing_checkout", fake_checkout)
    client = TestClient(api_index.app)

    response = client.post(
        "/v1/billing/checkout",
        json={
            "plan": "pro",
            "customer_email": "buyer@example.com",
            "success_url": "https://attacker.example/success/",
            "cancel_url": "javascript:alert(1)",
        },
    )

    assert response.status_code == 200
    assert captured["success_url"] == "https://cortexpersist.com/success/"
    assert captured["cancel_url"] == "https://cortexpersist.com/cancel/"
    assert captured["customer_email"] == "buyer@example.com"
    assert captured["metadata"] == {"plan": "pro"}


def test_proof_marks_fail_closed_without_storage(monkeypatch) -> None:
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
    client = TestClient(api_index.app)

    get_response = client.get("/v1/proof-marks")
    post_response = client.post(
        "/v1/proof-marks",
        json={"x": 0.5, "y": 0.25, "section": "hero"},
    )

    assert get_response.status_code == 503
    assert post_response.status_code == 503
    assert get_response.json()["detail"] == "Proof mark storage is not configured"


def test_create_proof_mark_quantizes_and_stores_without_identity(monkeypatch) -> None:
    commands: list[list] = []

    async def fake_redis_command(command: list) -> object:
        commands.append(command)
        match command[0]:
            case "INCR" if "rate" in command[1]:
                return 1
            case "EXPIRE":
                return 1
            case "INCR":
                return 42
            case "LPUSH":
                return 1
            case "LTRIM":
                return "OK"
        raise AssertionError(f"Unexpected Redis command: {command}")

    monkeypatch.setattr(api_index, "_redis_command", fake_redis_command)
    client = TestClient(api_index.app)

    response = client.post(
        "/v1/proof-marks",
        json={
            "x": 0.5312,
            "y": 0.9888,
            "section": "unknown-section",
            "ip": "203.0.113.9",
            "userAgent": "browser",
            "email": "visitor@example.com",
        },
    )

    assert response.status_code == 200
    mark = response.json()
    assert mark["x"] == 25 / 48
    assert mark["y"] == 158 / 160
    assert mark["section"] == "page"
    assert len(mark["hash"]) == 16
    assert set(mark) == {"x", "y", "section", "t", "hue", "hash"}

    stored_command = next(command for command in commands if command[0] == "LPUSH")
    assert stored_command[1] == api_index.PROOF_MARK_KEY
    stored_payload = stored_command[2]
    assert "203.0.113.9" not in stored_payload
    assert "browser" not in stored_payload
    assert "visitor@example.com" not in stored_payload


def test_proof_mark_rate_limit(monkeypatch) -> None:
    async def fake_redis_command(command: list) -> object:
        if command[0] == "INCR":
            return 999
        if command[0] == "EXPIRE":
            return 1
        raise AssertionError(f"Unexpected Redis command: {command}")

    monkeypatch.setenv("CORTEX_PROOF_MARKS_PER_MINUTE", "5")
    monkeypatch.setattr(api_index, "_redis_command", fake_redis_command)
    client = TestClient(api_index.app)

    response = client.post(
        "/v1/proof-marks",
        json={"x": 0.4, "y": 0.2, "section": "hero"},
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Proof mark rate limit exceeded"


def test_list_proof_marks_returns_recent_public_marks(monkeypatch) -> None:
    async def fake_redis_command(command: list) -> object:
        assert command == ["LRANGE", api_index.PROOF_MARK_KEY, 0, 1]
        return [
            '{"x":0.5,"y":0.25,"section":"hero","t":"2026-05-06T07:00:00Z","hue":"#d7ff5f","hash":"new"}',
            '{"x":0.25,"y":0.125,"section":"research","t":"2026-05-06T06:00:00Z","hash":"old"}',
            "not-json",
        ]

    monkeypatch.setattr(api_index, "_redis_command", fake_redis_command)
    client = TestClient(api_index.app)

    response = client.get("/v1/proof-marks?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "marks": [
            {
                "x": 0.25,
                "y": 0.125,
                "section": "research",
                "t": "2026-05-06T06:00:00Z",
                "hue": "#d7ff5f",
                "hash": "old",
            },
            {
                "x": 0.5,
                "y": 0.25,
                "section": "hero",
                "t": "2026-05-06T07:00:00Z",
                "hue": "#d7ff5f",
                "hash": "new",
            },
        ]
    }


def test_create_media_mark_uses_separate_public_store(monkeypatch) -> None:
    commands: list[list] = []

    async def fake_redis_command(command: list) -> object:
        commands.append(command)
        match command[0]:
            case "INCR" if "rate" in command[1]:
                return 1
            case "EXPIRE":
                return 1
            case "INCR":
                return 7
            case "LPUSH":
                return 1
            case "LTRIM":
                return "OK"
        raise AssertionError(f"Unexpected Redis command: {command}")

    monkeypatch.setattr(api_index, "_redis_command", fake_redis_command)
    client = TestClient(api_index.app)

    response = client.post(
        "/v1/media/marks",
        json={
            "x": 0.5312,
            "y": 0.4888,
            "section": "archivo",
            "email": "visitor@example.com",
        },
    )

    assert response.status_code == 200
    mark = response.json()
    assert mark["x"] == 30 / 56
    assert mark["y"] == 88 / 180
    assert mark["section"] == "archivo"
    assert len(mark["hash"]) == 16
    assert set(mark) == {"x", "y", "section", "t", "hue", "hash"}

    stored_command = next(command for command in commands if command[0] == "LPUSH")
    assert stored_command[1] == api_index.MEDIA_MARK_KEY
    assert "visitor@example.com" not in stored_command[2]


def test_list_media_marks_returns_recent_public_marks(monkeypatch) -> None:
    async def fake_redis_command(command: list) -> object:
        assert command == ["LRANGE", api_index.MEDIA_MARK_KEY, 0, 1]
        return [
            '{"x":0.5,"y":0.25,"section":"archivo","t":"2026-05-06T07:00:00Z","hue":"#d6b25e","hash":"new"}',
            '{"x":0.25,"y":0.125,"section":"playlist","t":"2026-05-06T06:00:00Z","hash":"old"}',
        ]

    monkeypatch.setattr(api_index, "_redis_command", fake_redis_command)
    client = TestClient(api_index.app)

    response = client.get("/v1/media/marks?limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "marks": [
            {
                "x": 0.25,
                "y": 0.125,
                "section": "playlist",
                "t": "2026-05-06T06:00:00Z",
                "hue": "#d6b25e",
                "hash": "old",
            },
            {
                "x": 0.5,
                "y": 0.25,
                "section": "archivo",
                "t": "2026-05-06T07:00:00Z",
                "hue": "#d6b25e",
                "hash": "new",
            },
        ]
    }
