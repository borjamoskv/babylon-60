from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import cortex.api.state as api_state
from cortex.routes.onboarding import SignupRequest, signup


class _DummyAuthManager:
    def __init__(self) -> None:
        self.list_keys = AsyncMock(return_value=[])
        self.create_key = AsyncMock(
            return_value=(
                "ctx_signup_key",
                SimpleNamespace(name="free-borja", tenant_id="user@example.com"),
            )
        )


@pytest.mark.asyncio
async def test_signup_blocks_remote_requests_by_default(monkeypatch) -> None:
    manager = _DummyAuthManager()
    previous = api_state.auth_manager
    api_state.auth_manager = manager
    request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.7"))

    try:
        with pytest.raises(HTTPException) as excinfo:
            await signup(
                SignupRequest(email="user@example.com", name="Borja"),
                request,
            )
    finally:
        api_state.auth_manager = previous

    assert excinfo.value.status_code == 403
    manager.create_key.assert_not_awaited()


@pytest.mark.asyncio
async def test_signup_allows_loopback_requests(monkeypatch) -> None:
    manager = _DummyAuthManager()
    previous = api_state.auth_manager
    api_state.auth_manager = manager
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    try:
        result = await signup(
            SignupRequest(email="user@example.com", name="Borja"),
            request,
        )
    finally:
        api_state.auth_manager = previous

    assert result.api_key == "ctx_signup_key"
    manager.create_key.assert_awaited_once()


@pytest.mark.asyncio
async def test_signup_allows_remote_when_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_ENABLE_PUBLIC_SIGNUP", "true")
    manager = _DummyAuthManager()
    previous = api_state.auth_manager
    api_state.auth_manager = manager
    request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.7"))

    try:
        result = await signup(
            SignupRequest(email="user@example.com", name="Borja"),
            request,
        )
    finally:
        api_state.auth_manager = previous

    assert result.api_key == "ctx_signup_key"
    manager.create_key.assert_awaited_once()
