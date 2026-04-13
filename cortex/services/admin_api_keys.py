from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from cortex.auth.models import APIKey, AuthResult

_TENANT_PATTERN = re.compile(r"^[a-z0-9_\-]+$", re.I)


class InvalidTenantIdError(ValueError):
    """Raised when a tenant id does not match the allowed pattern."""


class AdminAuthRequiredError(PermissionError):
    """Raised when admin authentication is required but missing."""


class AdminAuthInvalidError(PermissionError):
    """Raised when the provided bearer token is invalid or revoked."""


class AdminPermissionDeniedError(PermissionError):
    """Raised when the authenticated principal lacks admin permission."""


class ApiKeyManager(Protocol):
    """Minimal manager contract needed to provision admin API keys."""

    async def list_keys(self, tenant_id: str | None = None) -> list[APIKey]: ...

    async def authenticate_async(self, raw_key: str) -> AuthResult: ...

    async def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: list[str] | None = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]: ...


@dataclass(frozen=True)
class ApiKeyProvisioningResult:
    """Raw key plus persisted key metadata."""

    raw_key: str
    api_key: APIKey


async def verify_admin_authorization(
    manager: ApiKeyManager,
    authorization: str | None,
) -> None:
    """Enforce the admin-only bootstrap rule for key creation."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AdminAuthRequiredError

    token = authorization.split(" ", 1)[1]
    result = await manager.authenticate_async(token)

    if not result.authenticated:
        raise AdminAuthInvalidError

    if "admin" not in result.permissions:
        raise AdminPermissionDeniedError


async def provision_api_key(
    manager: ApiKeyManager,
    *,
    name: str,
    tenant_id: str,
    authorization: str | None,
) -> ApiKeyProvisioningResult:
    """Create the initial bootstrap key or require an admin bearer afterwards."""
    if not _TENANT_PATTERN.match(tenant_id):
        raise InvalidTenantIdError

    existing_keys = await manager.list_keys()
    if existing_keys:
        await verify_admin_authorization(manager, authorization)

    raw_key, api_key = await manager.create_key(
        name=name,
        tenant_id=tenant_id,
        permissions=["read", "write", "admin"],
    )
    return ApiKeyProvisioningResult(raw_key=raw_key, api_key=api_key)
