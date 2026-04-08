"""Authentication package exports.

Keep package import lightweight so schema/manager consumers do not depend on
FastAPI dependency modules at import time.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "APIKey",
    "AUTH_SCHEMA",
    "AuthManager",
    "AuthResult",
    "SQL_INSERT_KEY",
    "get_auth_manager",
    "require_auth",
    "require_consensus",
    "require_permission",
    "require_verified_permission",
    "reset_auth_manager",
]

if TYPE_CHECKING:
    from cortex.auth.deps import (
        require_auth,
        require_consensus,
        require_permission,
        require_verified_permission,
    )
    from cortex.auth.manager import AuthManager, get_auth_manager, reset_auth_manager
    from cortex.auth.models import APIKey, AuthResult
    from cortex.auth.schema import AUTH_SCHEMA, SQL_INSERT_KEY


_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "AuthManager": ("cortex.auth.manager", "AuthManager"),
    "get_auth_manager": ("cortex.auth.manager", "get_auth_manager"),
    "reset_auth_manager": ("cortex.auth.manager", "reset_auth_manager"),
    "APIKey": ("cortex.auth.models", "APIKey"),
    "AuthResult": ("cortex.auth.models", "AuthResult"),
    "AUTH_SCHEMA": ("cortex.auth.schema", "AUTH_SCHEMA"),
    "SQL_INSERT_KEY": ("cortex.auth.schema", "SQL_INSERT_KEY"),
    "require_auth": ("cortex.auth.deps", "require_auth"),
    "require_consensus": ("cortex.auth.deps", "require_consensus"),
    "require_permission": ("cortex.auth.deps", "require_permission"),
    "require_verified_permission": ("cortex.auth.deps", "require_verified_permission"),
}


def __getattr__(name: str) -> object:
    """Lazily load public auth symbols on first access."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'cortex.auth' has no attribute {name!r}")

    module_name, attr_name = target
    try:
        module = import_module(module_name)
        value = getattr(module, attr_name)
    except ImportError:
        value = None
    globals()[name] = value
    return value
