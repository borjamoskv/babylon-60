from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import cortex.api.state as api_state
from cortex.auth.models import AuthResult
from cortex.routes import stripe as stripe_routes


class _FakeStripe:
    class Customer:
        email = "tenant@example.com"

        @staticmethod
        def retrieve(customer_id: str):
            if customer_id == "cust_owner":
                return {"email": "tenant@example.com"}
            return {"email": "other@example.com"}

    class billing_portal:
        class Session:
            @staticmethod
            def create(*, customer: str, return_url: str):
                return SimpleNamespace(url=f"https://billing.example/{customer}")


@pytest.mark.asyncio
async def test_create_portal_session_rejects_cross_tenant_customer(monkeypatch) -> None:
    monkeypatch.setattr(stripe_routes, "_get_stripe", lambda: _FakeStripe)

    with pytest.raises(HTTPException) as excinfo:
        await stripe_routes.create_portal_session(
            stripe_routes.PortalRequest(customer_id="cust_other"),
            auth=AuthResult(
                authenticated=True,
                tenant_id="tenant@example.com",
                permissions=["read"],
                key_name="tenant-key",
            ),
        )

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Customer does not belong to this tenant"


@pytest.mark.asyncio
async def test_create_portal_session_allows_matching_tenant(monkeypatch) -> None:
    monkeypatch.setattr(stripe_routes, "_get_stripe", lambda: _FakeStripe)

    result = await stripe_routes.create_portal_session(
        stripe_routes.PortalRequest(customer_id="cust_owner"),
        auth=AuthResult(
            authenticated=True,
            tenant_id="tenant@example.com",
            permissions=["read"],
            key_name="tenant-key",
        ),
    )

    assert result == {"url": "https://billing.example/cust_owner"}


@pytest.mark.asyncio
async def test_provision_api_key_returns_actual_created_key() -> None:
    manager = SimpleNamespace(
        create_key=AsyncMock(
            return_value=(
                "ctx_real_created_key",
                SimpleNamespace(name="stripe-tenant@example.com"),
            )
        )
    )
    previous = api_state.auth_manager
    api_state.auth_manager = manager

    try:
        raw_key = await stripe_routes._provision_api_key("tenant@example.com", "pro")
    finally:
        api_state.auth_manager = previous

    assert raw_key == "ctx_real_created_key"
    manager.create_key.assert_awaited_once()
