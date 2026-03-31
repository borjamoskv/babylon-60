from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.gateway.adapters import openai_spoof


class FakeSovereignLLM:
    def __init__(self, temperature: float, max_tokens: int) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def __aenter__(self) -> FakeSovereignLLM:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def generate(self, prompt: str, system: str, intent: str):
        return SimpleNamespace(provider="test-provider", content="sovereign-ok")


def _client(auth_result: AuthResult | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(openai_spoof.router)
    if auth_result is not None:
        app.dependency_overrides[require_auth] = lambda: auth_result
    return TestClient(app)


def _patch_spoof(monkeypatch) -> dict[str, object]:
    calls: dict[str, object] = {}
    monkeypatch.setattr(openai_spoof, "SovereignLLM", FakeSovereignLLM)
    monkeypatch.setattr(
        openai_spoof._spoof_manager,
        "log_telemetry",
        lambda headers, body: calls.setdefault("logged_model", body["model"]),
    )
    monkeypatch.setattr(
        openai_spoof._spoof_manager,
        "to_cortex_prompt",
        lambda body: SimpleNamespace(
            working_memory=[{"role": "user", "content": "Hello from spoof"}],
            system_instruction="Stay strict",
            temperature=0.2,
            max_tokens=32,
            intent="general",
        ),
    )
    return calls


def test_openai_spoof_requires_auth(monkeypatch) -> None:
    _patch_spoof(monkeypatch)
    client = _client()

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 401


def test_openai_spoof_allows_authenticated_requests(monkeypatch) -> None:
    calls = _patch_spoof(monkeypatch)
    client = _client(
        AuthResult(
            authenticated=True,
            tenant_id="tenant-spoof",
            permissions=["read"],
            key_name="spoof-key",
        )
    )

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "sovereign-ok"
    assert response.json()["usage"]["completion_tokens"] > 0
    assert calls["logged_model"] == "gpt-4o-mini"
