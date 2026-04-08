"""CORTEX Auth — AuthManager and singleton access."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import secrets
import threading
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Optional, TypeVar

from cortex.auth.backends import BaseAuthBackend
from cortex.auth.models import APIKey, AuthResult

__all__ = ["AuthManager", "get_auth_manager", "reset_auth_manager"]

logger = logging.getLogger(__name__)
_T = TypeVar("_T")


class AuthManager:
    """Manages API key authentication for CORTEX.

    Refactored to support multiple storage backends (SQLite, AlloyDB, etc.).
    """

    KEY_LENGTH = 32  # 256-bit keys

    def __init__(self, backend: Optional[BaseAuthBackend | str] = None):
        """Initialize with an optional backend or db_path.

        Args:
            backend: BaseAuthBackend instance, or str (db_path) for SQLite.
        """
        if isinstance(backend, str):
            from cortex.auth.backends import SQLiteAuthBackend

            backend = SQLiteAuthBackend(backend)
        elif backend is None:
            from cortex.config import DB_PATH, PG_URL, RUNBOOT_MODE

            if RUNBOOT_MODE == "cloud" and PG_URL:
                from cortex.auth.backends import AlloyDBAuthBackend

                logger.info("AuthManager: Using Cloud Sovereign (PostgreSQL) backend")
                backend = AlloyDBAuthBackend(PG_URL)
            else:
                from cortex.auth.backends import SQLiteAuthBackend

                logger.info("AuthManager: Using Local Sovereign (SQLite) backend")
                backend = SQLiteAuthBackend(DB_PATH)
        self.backend = backend

    async def initialize(self) -> None:
        """Initialize the backend schema (async)."""
        await self.backend.initialize()

    def initialize_sync(self) -> None:
        """Initialize the backend schema (sync)."""
        if hasattr(self.backend, "initialize_sync"):
            self.backend.initialize_sync()  # type: ignore[reportAttributeAccessIssue]
            return

        self._run_coro_sync(self.initialize())

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _normalize_permissions(permissions: object) -> list[str]:
        if isinstance(permissions, str):
            loaded = json.loads(permissions)
            permissions = loaded
        if not isinstance(permissions, list):
            raise ValueError("Invalid permissions payload: expected list")
        if not all(isinstance(item, str) for item in permissions):
            raise ValueError("Invalid permissions payload: expected list[str]")
        return permissions

    @staticmethod
    def _api_key_from_row(row: dict[str, object]) -> APIKey:
        key_id = row["id"]
        if not isinstance(key_id, (int, str)):
            raise ValueError("Invalid API key row: id must be int or str")
        rate_limit = row["rate_limit"]
        if isinstance(rate_limit, int):
            normalized_rate_limit = rate_limit
        elif isinstance(rate_limit, str):
            normalized_rate_limit = int(rate_limit)
        else:
            raise ValueError("Invalid API key row: rate_limit must be int or str")
        return APIKey(
            id=key_id,
            name=str(row["name"]),
            key_prefix=str(row["key_prefix"]),
            tenant_id=str(row["tenant_id"]),
            role=str(row["role"]) if "role" in row else "user",
            permissions=AuthManager._normalize_permissions(row["permissions"]),
            created_at=str(row["created_at"]),
            last_used=str(row["last_used"]) if row.get("last_used") is not None else None,
            is_active=bool(row["is_active"]),
            rate_limit=normalized_rate_limit,
        )

    @staticmethod
    def _auth_result_from_row(row: dict[str, object]) -> AuthResult:
        return AuthResult(
            authenticated=True,
            tenant_id=str(row["tenant_id"]),
            role=str(row["role"]) if "role" in row else "user",
            permissions=AuthManager._normalize_permissions(row["permissions"]),
            key_name=str(row["name"]),
        )

    def _generate_key_material(self) -> tuple[str, str, str]:
        raw_key = f"ctx_{secrets.token_hex(self.KEY_LENGTH)}"
        return raw_key, self._hash_key(raw_key), raw_key[:12]

    def _resolve_auth_hash(self, raw_key: str) -> tuple[bool, str]:
        is_valid_format = bool(raw_key and raw_key.startswith("ctx_"))
        dummy_hash = self._hash_key("ctx_invalid_dummy_key_to_waste_time")
        key_hash = self._hash_key(raw_key) if is_valid_format else dummy_hash
        return is_valid_format, key_hash

    @staticmethod
    def _log_key_created(role: str, name: str, tenant_id: str) -> None:
        logger.info(
            "Created %s API key '%s' for tenant '%s'",
            role,
            name,
            tenant_id,
        )

    @staticmethod
    def _build_created_key(
        key_id: int | str,
        *,
        name: str,
        key_prefix: str,
        tenant_id: str,
        role: str,
        permissions: list[str],
        rate_limit: int,
    ) -> APIKey:
        return APIKey(
            id=key_id,
            name=name,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_used=None,
            is_active=True,
            rate_limit=rate_limit,
        )

    @staticmethod
    def _run_coro_sync(coro: Coroutine[object, object, _T]) -> _T:
        """Run an awaitable from sync code, even if a loop is already active."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result: list[_T] = []
        err: list[BaseException] = []
        event = threading.Event()

        def _runner() -> None:
            try:
                result.append(asyncio.run(coro))
            except BaseException as exc:  # noqa: BLE001 - relay to caller thread
                err.append(exc)
            finally:
                event.set()

        threading.Thread(target=_runner, daemon=True).start()
        event.wait()

        if err:
            raise err[0]
        return result[0]

    async def close(self) -> None:
        """Close the backend connections."""
        if hasattr(self.backend, "close"):
            await self.backend.close()  # type: ignore[reportAttributeAccessIssue]

    async def create_key(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: Optional[list[str]] = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Create a new API key. Returns (raw_key, APIKey metadata)."""
        if permissions is None:
            permissions = ["read", "write"]

        raw_key, key_hash, key_prefix = self._generate_key_material()

        key_id = await self.backend.store_key(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            rate_limit=rate_limit,
        )

        new_api_key = self._build_created_key(
            key_id=key_id,
            name=name,
            key_prefix=key_prefix,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            rate_limit=rate_limit,
        )
        self._log_key_created(role, name, tenant_id)
        return raw_key, new_api_key

    def create_key_sync(
        self,
        name: str,
        tenant_id: str = "default",
        role: str = "user",
        permissions: Optional[list[str]] = None,
        rate_limit: int = 100,
    ) -> tuple[str, APIKey]:
        """Synchronous wrapper for create_key (test fixtures / CLI).

        Handles both 'no event loop' and 'inside existing loop' cases.
        """
        if permissions is None:
            permissions = ["read", "write"]

        if hasattr(self.backend, "store_key_sync"):
            raw_key, key_hash, key_prefix = self._generate_key_material()
            key_id = self.backend.store_key_sync(  # type: ignore[reportAttributeAccessIssue]
                name=name,
                key_hash=key_hash,
                key_prefix=key_prefix,
                tenant_id=tenant_id,
                role=role,
                permissions=permissions,
                rate_limit=rate_limit,
            )
            new_api_key = self._build_created_key(
                key_id=key_id,
                name=name,
                key_prefix=key_prefix,
                tenant_id=tenant_id,
                role=role,
                permissions=permissions,
                rate_limit=rate_limit,
            )
            self._log_key_created(role, name, tenant_id)
            return raw_key, new_api_key

        return self._run_coro_sync(
            self.create_key(
                name,
                tenant_id=tenant_id,
                role=role,
                permissions=permissions,
                rate_limit=rate_limit,
            )
        )

    def authenticate(self, raw_key: str) -> AuthResult:
        """Synchronous wrapper for authentication.

        Authenticate a key synchronously (for legacy test fixtures/CLI).
        In v6 Sovereign Cloud, use authenticate_async whenever possible.
        """
        if hasattr(self.backend, "get_key_by_hash_sync"):
            is_valid_format, key_hash = self._resolve_auth_hash(raw_key)

            if not is_valid_format:
                return AuthResult(authenticated=False, error="Invalid key format")

            row = self.backend.get_key_by_hash_sync(  # type: ignore[reportAttributeAccessIssue]
                key_hash
            )
            if not row:
                return AuthResult(authenticated=False, error="Invalid or revoked key")

            if hasattr(self.backend, "update_last_used_sync"):
                self.backend.update_last_used_sync(row["id"])  # type: ignore[reportAttributeAccessIssue]

            return self._auth_result_from_row(row)

        return self._run_coro_sync(self.authenticate_async(raw_key))

    async def authenticate_async(self, raw_key: str) -> AuthResult:
        """Fully async authentication."""
        is_valid_format, key_hash = self._resolve_auth_hash(raw_key)

        if not is_valid_format:
            return AuthResult(authenticated=False, error="Invalid key format")

        row = await self.backend.get_key_by_hash(key_hash)
        if not row:
            return AuthResult(authenticated=False, error="Invalid or revoked key")

        await self.backend.update_last_used(row["id"])

        return self._auth_result_from_row(row)

    async def list_keys(self, tenant_id: Optional[str] = None) -> list[APIKey]:
        """List all API keys."""
        rows = await self.backend.list_keys(tenant_id)
        return [self._api_key_from_row(r) for r in rows]

    async def revoke_key(self, key_id: int | str) -> bool:
        """Revoke an API key."""
        return await self.backend.revoke_key(key_id)


# ─── Singleton ────────────────────────────────────────────────────────

_auth_manager: AuthManager | None = None
_auth_lock = threading.Lock()


def get_auth_manager() -> AuthManager:
    """Lazy-load the global AuthManager instance (thread-safe)."""
    global _auth_manager  # noqa: PLW0603
    if _auth_manager is None:
        with _auth_lock:
            if _auth_manager is None:
                _auth_manager = AuthManager()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the global AuthManager instance (useful for tests)."""
    global _auth_manager  # noqa: PLW0603
    _auth_manager = None
