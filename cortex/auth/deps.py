"""CORTEX Auth — FastAPI dependencies."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.auth.rbac import RBAC, Permission
from cortex.crypto import get_default_encrypter

__all__ = [
    "require_auth",
    "require_consensus",
    "require_permission",
    "require_verified_permission",
]

logger = logging.getLogger(__name__)


def _permission_name(permission: str | Permission) -> str:
    if isinstance(permission, Permission):
        return permission.value
    return permission


def _auth_has_permission(auth: AuthResult, permission: str | Permission) -> bool:
    has_perm = False
    if isinstance(permission, str) and permission in auth.permissions:
        has_perm = True
    elif isinstance(permission, Permission):
        has_perm = RBAC.has_permission(auth.role, permission)

    if not has_perm and str(permission) in auth.permissions:
        has_perm = True

    return has_perm


def _normalize_claim(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _extract_fact_id(candidate: Any) -> int | None:
    if isinstance(candidate, dict):
        raw_fact_id = candidate.get("fact_id") or candidate.get("id")
        if isinstance(raw_fact_id, int):
            return raw_fact_id
        if isinstance(raw_fact_id, str) and raw_fact_id.isdigit():
            return int(raw_fact_id)
        return None

    raw_fact_id = getattr(candidate, "fact_id", getattr(candidate, "id", None))
    if isinstance(raw_fact_id, int):
        return raw_fact_id
    if isinstance(raw_fact_id, str) and raw_fact_id.isdigit():
        return int(raw_fact_id)
    return None


def _extract_fact_content(candidate: Any) -> str:
    if isinstance(candidate, dict):
        return str(candidate.get("content") or "")
    return str(getattr(candidate, "content", "") or "")


def _extract_consensus_score(candidate: Any) -> float:
    if isinstance(candidate, dict):
        if candidate.get("consensus_score") is not None:
            return float(candidate["consensus_score"] or 0.0)

        meta = candidate.get("meta") or candidate.get("metadata") or {}
        if isinstance(meta, dict):
            return float(meta.get("consensus_score", 0.0) or 0.0)
        return 0.0

    consensus_score = getattr(candidate, "consensus_score", None)
    if consensus_score is not None:
        return float(consensus_score or 0.0)

    meta = getattr(candidate, "meta", None)
    if isinstance(meta, dict):
        return float(meta.get("consensus_score", 0.0) or 0.0)

    return 0.0


async def _search_consensus_candidates(
    engine: Any,
    *,
    claim: str,
    tenant_id: str,
    project: str | None,
    top_k: int,
) -> list[Any]:
    search_fn = getattr(engine, "search", None) or getattr(engine, "query", None)
    if not callable(search_fn):
        return []

    try:
        return await search_fn(
            query=claim,
            tenant_id=tenant_id,
            project=project,
            top_k=top_k,
        )
    except TypeError:
        return await search_fn(claim, tenant_id=tenant_id, project=project, top_k=top_k)


async def _scan_claim_candidates(
    engine: Any,
    *,
    claim: str,
    tenant_id: str,
    project: str | None,
) -> list[int]:
    session = getattr(engine, "session", None)
    if not callable(session):
        return []

    enc = get_default_encrypter()
    normalized_claim = _normalize_claim(claim)
    query = (
        "SELECT id, content FROM facts "
        "WHERE tenant_id = ? AND valid_until IS NULL AND is_tombstoned = 0"
    )
    params: list[Any] = [tenant_id]
    if project is not None:
        query += " AND project = ?"
        params.append(project)

    candidate_ids: list[int] = []
    async with engine.session() as conn:
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    for fact_id, raw_content in rows:
        try:
            content = enc.decrypt_str(raw_content, tenant_id=tenant_id) or ""
        except (RuntimeError, ValueError):
            continue

        if _normalize_claim(content) == normalized_claim:
            candidate_ids.append(int(fact_id))

    return candidate_ids


async def require_auth(
    request: Request,
    authorization: str | None = Header(
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

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_invalid_key_format", lang),
        )

    manager = get_auth_manager()
    result = await manager.authenticate_async(parts[1])
    if not result.authenticated:
        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise HTTPException(status_code=401, detail=error_msg)

    # SECURE LINK: Bind the dynamic tenant context to the authenticated identity
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
        has_perm = _auth_has_permission(auth, permission)
        if not has_perm:
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            perm_name = _permission_name(permission)
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=perm_name)
            raise HTTPException(status_code=403, detail=detail)
        return auth

    return checker


async def require_consensus(
    claim: str,
    min_score: float = 1.6,
    *,
    engine: Any,
    tenant_id: str = "default",
    project: str | None = None,
    top_k: int = 5,
) -> bool:
    """Verify a claim has reached sufficient consensus.

    Used for 'Sovereign Gate' high-stakes authorizations.
    """
    normalized_claim = _normalize_claim(claim)
    if not normalized_claim:
        return False

    if engine is None:
        raise ValueError("engine must be provided to require_consensus")

    if tenant_id == "default" and hasattr(engine, "_resolve_tenant"):
        tenant_id = engine._resolve_tenant(tenant_id)

    facts = await _search_consensus_candidates(
        engine,
        claim=claim,
        tenant_id=tenant_id,
        project=project,
        top_k=top_k,
    )
    exact_candidates = [
        fact for fact in facts if _normalize_claim(_extract_fact_content(fact)) == normalized_claim
    ]
    ordered_candidates = exact_candidates or list(facts[:1])

    candidate_ids: list[int] = []
    for candidate in ordered_candidates:
        fact_id = _extract_fact_id(candidate)
        if fact_id is not None and fact_id not in candidate_ids:
            candidate_ids.append(fact_id)

    for fact_id in await _scan_claim_candidates(
        engine,
        claim=claim,
        tenant_id=tenant_id,
        project=project,
    ):
        if fact_id not in candidate_ids:
            candidate_ids.append(fact_id)

    score = 0.0
    get_fact = getattr(engine, "get_fact", None)
    if callable(get_fact):
        for fact_id in candidate_ids:
            fact = await get_fact(fact_id, tenant_id=tenant_id)
            if fact is None:
                continue
            score = max(score, _extract_consensus_score(fact))
    else:
        for candidate in ordered_candidates:
            score = max(score, _extract_consensus_score(candidate))

    if score < min_score:
        logger.warning(
            "Sovereign Gate: Claim '%s' failed consensus (%.2f < %.2f)",
            claim,
            score,
            min_score,
        )
        return False
    return True


def require_verified_permission(
    permission: str | Permission,
    min_consensus: float = 1.6,
):
    """Sovereign Gate: Requires both permission AND verified claim."""

    async def sovereign_checker(
        request: Request,
        auth: AuthResult = Depends(require_auth),
    ) -> AuthResult:
        if not _auth_has_permission(auth, permission):
            from cortex.utils.i18n import get_trans

            lang = request.headers.get("Accept-Language", "en")
            detail = get_trans(
                "error_missing_permission",
                lang,
            ).format(permission=_permission_name(permission))
            raise HTTPException(status_code=403, detail=detail)

        from cortex.api.deps import get_async_engine

        engine = get_async_engine(request)
        permission_name = _permission_name(permission)
        claim_subject = (auth.key_name or auth.tenant_id).strip() or auth.tenant_id

        has_consensus = await require_consensus(
            f"Permission {permission_name} granted to {claim_subject}",
            min_score=min_consensus,
            engine=engine,
            tenant_id=auth.tenant_id,
        )
        if not has_consensus:
            detail = f"Sovereign Gate: Action requires consensus (min: {min_consensus})"
            raise HTTPException(status_code=403, detail=detail)

        return auth

    return sovereign_checker
