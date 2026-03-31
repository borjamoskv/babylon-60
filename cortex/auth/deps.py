"""CORTEX Auth — FastAPI dependencies."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request, WebSocket, WebSocketException, status

from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.auth.rbac import RBAC, Permission

__all__ = [
    "require_auth",
    "require_consensus",
    "require_permission",
    "require_verified_permission",
    "require_websocket_auth",
    "require_websocket_permission",
]

logger = logging.getLogger(__name__)

_DEFAULT_CONSENSUS_THRESHOLD = 0.8


def _parse_bearer_token(authorization: str | None) -> str | None:
    """Extract the raw API key from a Bearer header."""
    if not authorization:
        return None

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid key format")

    return parts[1]


def _auth_has_permission(auth: AuthResult, permission: str | Permission) -> bool:
    """Check whether an authenticated identity satisfies a permission requirement."""
    if isinstance(permission, str) and permission in auth.permissions:
        return True
    if isinstance(permission, Permission) and RBAC.has_permission(auth.role, permission):
        return True
    return str(permission) in auth.permissions


def _normalize_claim_text(value: str) -> str:
    """Normalize claim text for exact-match authorization checks."""
    return " ".join((value or "").split()).strip().casefold()


def _extract_consensus_score(fact: object) -> float:
    """Read the canonical consensus score from a fact-like object."""
    if isinstance(fact, dict):
        score = fact.get("consensus_score")
        if score is None:
            meta = fact.get("meta")
            if isinstance(meta, dict):
                score = meta.get("consensus_score")
        if score is not None:
            return float(score)
    return 0.0


def _resolve_async_engine(explicit_engine: Any | None = None) -> Any:
    """Resolve the async engine from the explicit argument or API state."""
    if explicit_engine is not None:
        return explicit_engine

    import cortex.api.state as api_state

    engine = getattr(api_state, "async_engine", None)
    if engine is None:
        raise RuntimeError("Async engine not initialized")
    return engine


async def require_auth(
    request: Request,
    authorization: Optional[str] = Header(
        None,
        description="Bearer <api-key>",
    ),
) -> AuthResult:
    """Extract and validate API key from Authorization header."""
    from cortex.utils.i18n import get_trans

    lang = request.headers.get("Accept-Language", "en")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_missing_auth", lang),
        )

    try:
        raw_key = _parse_bearer_token(authorization)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_invalid_key_format", lang),
        )
    assert raw_key is not None

    manager = get_auth_manager()
    result = await manager.authenticate_async(raw_key)
    if not result.authenticated:
        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise HTTPException(status_code=401, detail=error_msg)

    # SECURE LINK: Bind the dynamic tenant context to the authenticated identity
    from cortex.extensions.security.tenant import tenant_id_var

    tenant_id_var.set(result.tenant_id)

    return result


async def require_websocket_auth(websocket: WebSocket) -> AuthResult:
    """Authenticate a WebSocket handshake via Authorization header or query param."""
    authorization = websocket.headers.get("authorization")
    raw_key: str | None

    if authorization:
        try:
            raw_key = _parse_bearer_token(authorization)
        except ValueError as exc:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid Authorization header",
            ) from exc
    else:
        raw_key = websocket.query_params.get("api_key") or websocket.query_params.get("token")

    if not raw_key:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication required",
        )

    manager = get_auth_manager()
    result = await manager.authenticate_async(raw_key)
    if not result.authenticated:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=result.error or "Invalid or revoked key",
        )

    from cortex.extensions.security.tenant import tenant_id_var

    tenant_id_var.set(result.tenant_id)
    return result


def require_permission(permission: str | Permission):
    """Factory for permission-checking dependencies.

    Supports both legacy string permissions and CORTEX v6 Permission enums.
    """

    async def checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        if not _auth_has_permission(auth, permission):
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            perm_name = permission.name if isinstance(permission, Permission) else permission
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=perm_name)
            raise HTTPException(status_code=403, detail=detail)
        return auth

    return checker


def require_websocket_permission(permission: str | Permission):
    """Factory for permission-checking WebSocket dependencies."""

    async def checker(
        websocket: WebSocket,
        auth: AuthResult = Depends(require_websocket_auth),
    ) -> AuthResult:
        if not _auth_has_permission(auth, permission):
            perm_name = permission.name if isinstance(permission, Permission) else permission
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Missing permission: {perm_name}",
            )
        return auth

    return checker


async def require_consensus(
    claim: str,
    min_score: float = _DEFAULT_CONSENSUS_THRESHOLD,
    engine: Any | None = None,
    tenant_id: str = "default",
) -> bool:
    """Verify a claim has reached sufficient consensus.

    Used for 'Sovereign Gate' high-stakes authorizations.
    """
    engine = _resolve_async_engine(engine)
    normalized_claim = _normalize_claim_text(claim)
    if not normalized_claim:
        return False

    candidates = await engine.search(query=claim, top_k=5, tenant_id=tenant_id)
    for candidate in candidates:
        if _normalize_claim_text(getattr(candidate, "content", "")) != normalized_claim:
            continue
        fact_id = getattr(candidate, "fact_id", None)
        if fact_id is None:
            continue
        fact = await engine.get_fact(fact_id, tenant_id=tenant_id)
        if fact is None:
            continue
        score = _extract_consensus_score(fact)
        if score < min_score:
            logger.warning(
                "Sovereign Gate: Claim '%s' failed consensus (%.2f < %.2f)",
                claim,
                score,
                min_score,
            )
            return False
        return True

    logger.warning("Sovereign Gate: Claim '%s' has no exact verified fact", claim)
    return False


def require_verified_permission(
    permission: str,
    min_consensus: float = _DEFAULT_CONSENSUS_THRESHOLD,
):
    """Sovereign Gate: Requires both permission AND verified claim."""

    async def sovereign_checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        if permission not in auth.permissions:
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=permission)
            raise HTTPException(status_code=403, detail=detail)

        engine = _resolve_async_engine(getattr(request.app.state, "async_engine", None))
        has_consensus = await require_consensus(
            f"Permission {permission} granted to {auth.key_name or auth.tenant_id}",
            min_score=min_consensus,
            engine=engine,
            tenant_id=auth.tenant_id,
        )
        if not has_consensus:
            detail = f"Sovereign Gate: Action requires consensus (min: {min_consensus})"
            raise HTTPException(status_code=403, detail=detail)

        return auth

    return sovereign_checker
