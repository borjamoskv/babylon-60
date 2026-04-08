from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cortex.api.state as api_state
import cortex.auth.manager as auth_manager_module
from cortex.auth.manager import AuthManager
from cortex.routes import admin as admin_router


class _TrackingAuthBackend:
    def __init__(self) -> None:
        self.closed = False
        self.update_started = asyncio.Event()
        self.allow_update_finish = asyncio.Event()
        self.update_completed = False

    async def initialize(self) -> None:
        return None

    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        return {
            "id": 7,
            "name": "alpha-admin",
            "tenant_id": "tenant-alpha",
            "role": "admin",
            "permissions": ["admin"],
        }

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        return 1

    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        return []

    async def revoke_key(self, key_id: int | str) -> bool:
        return True

    async def update_last_used(self, key_id: int | str) -> None:
        self.update_started.set()
        await self.allow_update_finish.wait()
        self.update_completed = True

    async def close(self) -> None:
        self.closed = True


class _SyncCapableAuthBackend:
    def __init__(self) -> None:
        self.initialize_sync_called = False
        self.store_key_sync_called = False
        self.get_key_by_hash_sync_called = False
        self.update_last_used_sync_calls: list[int | str] = []

    async def initialize(self) -> None:
        raise AssertionError("async initialize should not be used in sync fast-path tests")

    def initialize_sync(self) -> None:
        self.initialize_sync_called = True

    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        raise AssertionError("async lookup should not be used in sync fast-path tests")

    def get_key_by_hash_sync(self, key_hash: str) -> dict[str, Any] | None:
        self.get_key_by_hash_sync_called = True
        return {
            "id": 11,
            "name": "sync-admin",
            "tenant_id": "tenant-sync",
            "role": "admin",
            "permissions": '["admin","read"]',
        }

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        raise AssertionError("async store should not be used in sync fast-path tests")

    def store_key_sync(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        self.store_key_sync_called = True
        return 99

    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        return []

    async def revoke_key(self, key_id: int | str) -> bool:
        return True

    async def update_last_used(self, key_id: int | str) -> None:
        raise AssertionError("async update should not be used in sync fast-path tests")

    def update_last_used_sync(self, key_id: int | str) -> None:
        self.update_last_used_sync_calls.append(key_id)

    async def close(self) -> None:
        return None


class _MalformedPermissionsBackend:
    async def initialize(self) -> None:
        return None

    async def get_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        return {
            "id": 13,
            "name": "bad-admin",
            "tenant_id": "tenant-bad",
            "role": "admin",
            "permissions": '{"admin": true}',
        }

    async def store_key(
        self,
        name: str,
        key_hash: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> int:
        return 1

    async def list_keys(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": 13,
                "name": "bad-admin",
                "key_prefix": "ctx_bad_key",
                "tenant_id": "tenant-bad",
                "role": "admin",
                "permissions": '{"admin": true}',
                "created_at": "2026-04-07T00:00:00+00:00",
                "last_used": None,
                "is_active": 1,
                "rate_limit": 100,
            }
        ]

    async def revoke_key(self, key_id: int | str) -> bool:
        return True

    async def update_last_used(self, key_id: int | str) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
def admin_client(tmp_path) -> Iterator[tuple[AuthManager, TestClient]]:
    db_path = tmp_path / "auth.db"
    manager = AuthManager(str(db_path))
    manager.initialize_sync()

    previous_api_manager = api_state.auth_manager
    previous_global_manager = auth_manager_module._auth_manager
    api_state.auth_manager = manager
    auth_manager_module._auth_manager = manager
    admin_router._rate_limiter._buckets.clear()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Iterator[None]:
        try:
            yield
        finally:
            await manager.close()

    app = FastAPI(lifespan=lifespan)
    app.include_router(admin_router.router)
    client = TestClient(app)

    try:
        yield manager, client
    finally:
        client.close()
        api_state.auth_manager = previous_api_manager
        auth_manager_module._auth_manager = previous_global_manager


def test_create_api_key_bootstrap_is_single_use(admin_client) -> None:
    manager, client = admin_client

    first = client.post(
        "/v1/admin/keys",
        params={"name": "bootstrap-admin", "tenant_id": "tenant-alpha"},
    )
    if first.status_code != 200:
        print(f"DEBUG: {first.json()}")
    assert first.status_code == 200
    assert first.json()["tenant_id"] == "tenant-alpha"

    keys = asyncio.run(manager.list_keys())
    assert len(keys) == 1

    second = client.post(
        "/v1/admin/keys",
        params={"name": "should-fail", "tenant_id": "tenant-alpha"},
    )
    assert second.status_code == 401


def test_create_api_key_rejects_invalid_tenant_id(admin_client) -> None:
    manager, client = admin_client

    response = client.post(
        "/v1/admin/keys",
        params={"name": "bootstrap-admin", "tenant_id": "tenant alpha"},
    )

    assert response.status_code == 400
    assert asyncio.run(manager.list_keys()) == []


def test_list_api_keys_is_scoped_to_authenticated_tenant(admin_client) -> None:
    manager, client = admin_client

    token_alpha, _ = manager.create_key_sync(
        "alpha-admin",
        tenant_id="tenant-alpha",
        permissions=["read", "write", "admin"],
    )
    manager.create_key_sync("alpha-worker", tenant_id="tenant-alpha", permissions=["read"])

    token_beta, _ = manager.create_key_sync(
        "beta-admin",
        tenant_id="tenant-beta",
        permissions=["read", "write", "admin"],
    )
    manager.create_key_sync("beta-worker", tenant_id="tenant-beta", permissions=["read"])

    alpha_response = client.get(
        "/v1/admin/keys",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert alpha_response.status_code == 200
    assert {item["tenant_id"] for item in alpha_response.json()} == {"tenant-alpha"}
    assert {item["name"] for item in alpha_response.json()} == {"alpha-admin", "alpha-worker"}

    beta_response = client.get(
        "/v1/admin/keys",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert beta_response.status_code == 200
    assert {item["tenant_id"] for item in beta_response.json()} == {"tenant-beta"}
    assert {item["name"] for item in beta_response.json()} == {"beta-admin", "beta-worker"}


def test_invalid_auth_does_not_assign_default_tenant(admin_client) -> None:
    manager, _ = admin_client

    result = asyncio.run(manager.authenticate_async("not-a-valid-key"))

    assert result.authenticated is False
    assert result.tenant_id == ""


def test_initialize_and_create_key_sync_prefer_sync_backend_methods() -> None:
    backend = _SyncCapableAuthBackend()
    manager = AuthManager(backend)

    manager.initialize_sync()
    raw_key, api_key = manager.create_key_sync(
        "sync-admin",
        tenant_id="tenant-sync",
        permissions=["admin", "read"],
    )

    assert backend.initialize_sync_called is True
    assert backend.store_key_sync_called is True
    assert raw_key.startswith("ctx_")
    assert api_key.id == 99
    assert api_key.tenant_id == "tenant-sync"
    assert api_key.permissions == ["admin", "read"]


def test_authenticate_prefers_sync_backend_methods() -> None:
    backend = _SyncCapableAuthBackend()
    manager = AuthManager(backend)

    result = manager.authenticate("ctx_sync_token")

    assert backend.get_key_by_hash_sync_called is True
    assert backend.update_last_used_sync_calls == [11]
    assert result.authenticated is True
    assert result.tenant_id == "tenant-sync"
    assert result.permissions == ["admin", "read"]


@pytest.mark.asyncio
async def test_sync_wrappers_work_inside_active_event_loop_with_sync_backend() -> None:
    backend = _SyncCapableAuthBackend()
    manager = AuthManager(backend)

    manager.initialize_sync()
    raw_key, api_key = manager.create_key_sync(
        "loop-admin",
        tenant_id="tenant-loop",
        permissions=["admin", "read"],
    )
    result = manager.authenticate(raw_key)

    assert backend.initialize_sync_called is True
    assert backend.store_key_sync_called is True
    assert backend.get_key_by_hash_sync_called is True
    assert backend.update_last_used_sync_calls == [11]
    assert api_key.id == 99
    assert result.authenticated is True


@pytest.mark.asyncio
async def test_authenticate_async_rejects_malformed_permission_payload() -> None:
    manager = AuthManager(_MalformedPermissionsBackend())

    with pytest.raises(ValueError, match="Invalid permissions payload"):
        await manager.authenticate_async("ctx_bad_token")


@pytest.mark.asyncio
async def test_list_keys_rejects_malformed_permission_payload() -> None:
    manager = AuthManager(_MalformedPermissionsBackend())

    with pytest.raises(ValueError, match="Invalid permissions payload"):
        await manager.list_keys()


@pytest.mark.asyncio
async def test_authenticate_async_waits_for_last_used_update() -> None:
    backend = _TrackingAuthBackend()
    manager = AuthManager(backend)

    auth_task = asyncio.create_task(manager.authenticate_async("ctx_test_token"))
    await backend.update_started.wait()

    assert auth_task.done() is False
    assert backend.update_completed is False

    backend.allow_update_finish.set()
    result = await auth_task

    assert result.authenticated is True
    assert backend.update_completed is True
    await manager.close()
    assert backend.closed is True
