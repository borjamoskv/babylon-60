"""
CORTEX v5.1 — Admin & Governance Router.

High-privilege endpoints for project management, API key governance,
and session handoff orchestration. Enforces strict RBAC and input validation.

Sovereign 130/100 — Pydantic responses, structured logging, TOCTOU-safe paths.
"""

import logging
import time
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.requests import Request

import cortex.api.state as api_state
from cortex import __version__
from cortex.api.deps import get_engine
from cortex.auth import AuthResult, get_auth_manager, require_permission
from cortex.database.schema import SCHEMA_VERSION
from cortex.engine import CortexEngine
from cortex.routes.admin_health_probes import build_health_probes as _build_health_probes
from cortex.routes.middleware import AuditLogger, RateLimiter, SelfHealingHook
from cortex.services.admin_api_keys import (
    AdminAuthInvalidError,
    AdminAuthRequiredError,
    AdminPermissionDeniedError,
    InvalidTenantIdError,
    provision_api_key,
)
from cortex.services.admin_health import build_deep_health_response, execute_health_probes
from cortex.services.project_export import (
    ExportPathOutsideWorkspaceError,
    InvalidExportPathCharsError,
    InvalidExportPathError,
    ProjectExportExecutionError,
    UnsupportedExportFormatError,
    export_project_artifact,
)
from cortex.types.models import (
    ApiKeyListItem,
    ApiKeyResponse,
    DeepHealthResponse,
    ExportResponse,
    StatusResponse,
)
from cortex.utils.i18n import DEFAULT_LANGUAGE, get_trans

if TYPE_CHECKING:
    from cortex.auth.manager import AuthManager

__all__ = [
    "create_api_key",
    "deep_health_check",
    "export_project",
    "generate_handoff_context",
    "get_system_status",
    "list_api_keys",
]

# ─── Middleware Instances ─────────────────────────────────────────────
_rate_limiter = RateLimiter(max_requests=10, window_seconds=1.0)
_audit_logger = AuditLogger()

router = APIRouter(
    tags=["governance"],
    dependencies=[Depends(_rate_limiter), Depends(_audit_logger)],
)
logger = logging.getLogger("cortex.admin")

# Maximum facts to export in a single operation
_MAX_EXPORT_FACTS = 100_000
# ─── Shared Helpers ──────────────────────────────────────────────────


def _get_lang(request: Request) -> str:
    """Extract Accept-Language from request with fallback."""
    return request.headers.get("Accept-Language", DEFAULT_LANGUAGE)


def _get_auth_manager() -> "AuthManager":
    """Resolve the active auth manager singleton."""
    return api_state.auth_manager or get_auth_manager()


# Health probes → cortex.routes.admin_health_probes


def _get_raw_conn(engine: CortexEngine) -> object:
    """Isolate private access to engine's raw connection."""
    return engine._get_sync_conn()


# ─── Project Management ──────────────────────────────────────────────


@router.get("/v1/projects/{project}/export", response_model=ExportResponse)
async def export_project(
    project: str,
    request: Request,
    path: Optional[str] = Query(None),
    fmt: str = Query("json", alias="format"),
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> ExportResponse:
    """Sovereign Export — dumps project memory to a secure JSON artifact.

    Enforces path incarceration to prevent directory traversal.
    """
    lang = _get_lang(request)
    try:
        export_result = await export_project_artifact(
            engine=engine,
            project=project,
            path=path,
            fmt=fmt,
            max_facts=_MAX_EXPORT_FACTS,
        )
    except UnsupportedExportFormatError:
        raise HTTPException(status_code=400, detail=get_trans("error_json_only", lang)) from None
    except InvalidExportPathCharsError:
        raise HTTPException(
            status_code=400,
            detail=get_trans("error_invalid_path_chars", lang),
        ) from None
    except ExportPathOutsideWorkspaceError:
        raise HTTPException(
            status_code=400,
            detail=get_trans("error_path_workspace", lang),
        ) from None
    except InvalidExportPathError:
        raise HTTPException(
            status_code=400,
            detail=get_trans("error_invalid_input", lang),
        ) from None
    except ProjectExportExecutionError as exc:
        logger.error(
            "Export failure: project=%s error=%s",
            project,
            exc.__cause__ or exc,
        )
        SelfHealingHook.trigger(
            exc.__cause__ or exc,
            {"endpoint": "export_project", "project": project},
        )
        raise HTTPException(
            status_code=500,
            detail=get_trans("error_export_failed", lang),
        ) from None

    logger.info(
        "Export completed: project=%s path=%s",
        project,
        export_result.artifact,
    )
    return ExportResponse(
        project=project,
        artifact=str(export_result.artifact),
        message=get_trans("info_export_success", lang),
    )


# ─── Health & Diagnostics ────────────────────────────────────────────


@router.get(
    "/v1/health/deep",
    tags=["health"],
    response_model=DeepHealthResponse,
)
async def deep_health_check(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> DeepHealthResponse:
    """Deep Health Check — probes all CORTEX subsystems.

    Returns 200 if all checks pass, 503 if any subsystem is degraded.
    Designed for Kubernetes liveness/readiness probes.
    """
    start = time.monotonic()

    conn = _get_raw_conn(engine)
    probes = _build_health_probes(conn, request, SCHEMA_VERSION)

    try:
        checks, overall_healthy = await execute_health_probes(probes)
    except (OSError, RuntimeError) as exc:
        logger.error("Deep health check failure: %s", exc)
        SelfHealingHook.trigger(
            exc,
            {"endpoint": "deep_health_check"},
        )
        raise HTTPException(
            status_code=503,
            detail="Health check failed",
        ) from None

    from cortex.routes.context import get_p95_context_latency

    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    result = build_deep_health_response(
        overall_healthy=overall_healthy,
        version=__version__,
        schema_version=SCHEMA_VERSION,
        checks=checks,
        latency_ms=elapsed_ms,
        p95_latency_ms=get_p95_context_latency(),
    )

    if not overall_healthy:
        return JSONResponse(  # type: ignore[return-value]
            content=result.model_dump(),
            status_code=503,
        )
    return result


@router.get("/v1/status", response_model=StatusResponse)
async def get_system_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    engine: CortexEngine = Depends(get_engine),
) -> StatusResponse:
    """Expose engine diagnostics and memory health metrics."""
    lang = _get_lang(request)
    try:
        stats = await engine.stats()
        return StatusResponse(
            version=__version__,
            total_facts=stats["total_facts"],
            active_facts=stats["active_facts"],
            deprecated=stats["deprecated_facts"],
            projects=stats["project_count"],
            embeddings=stats["embeddings"],
            transactions=stats["transactions"],
            db_size_mb=stats["db_size_mb"],
        )
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.error("Status check failure: %s", exc)
        SelfHealingHook.trigger(exc, {"endpoint": "get_system_status"})
        raise HTTPException(
            status_code=500, detail=get_trans("error_status_unavailable", lang)
        ) from None


# ─── API Key Governance ─────────────────────────────────────────────


class _HandoffBody(BaseModel):
    """Optional body for handoff request."""

    session: Optional[dict] = Field(None, description="Session metadata for handoff context")


@router.post("/v1/admin/keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: Request,
    name: str = Query(..., min_length=3, max_length=64),
    tenant_id: str = Query("default"),
    authorization: Optional[str] = Header(None),
) -> ApiKeyResponse:
    """Sovereign Key Provisioning.

    First key is self-provisioned (bootstrap).
    Subsequent keys require 'admin' permission.
    """
    lang = _get_lang(request)
    manager = _get_auth_manager()
    try:
        provisioned = await provision_api_key(
            manager,
            name=name,
            tenant_id=tenant_id,
            authorization=authorization,
        )
    except InvalidTenantIdError:
        raise HTTPException(status_code=400, detail=get_trans("error_invalid_input", lang)) from None
    except AdminAuthRequiredError:
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_auth_required", lang),
        ) from None
    except AdminAuthInvalidError:
        raise HTTPException(
            status_code=401,
            detail=get_trans("error_invalid_revoked_key", lang),
        ) from None
    except AdminPermissionDeniedError:
        detail = get_trans(
            "error_missing_permission",
            lang,
        ).format(permission="admin")
        raise HTTPException(status_code=403, detail=detail) from None

    api_key = provisioned.api_key

    logger.info(
        "API key created: name=%s tenant=%s prefix=%s",
        name,
        tenant_id,
        api_key.key_prefix,
    )

    return ApiKeyResponse(
        key=provisioned.raw_key,
        name=api_key.name,
        prefix=api_key.key_prefix,
        tenant_id=api_key.tenant_id,
        message=get_trans("info_key_warning", lang),
    )


@router.get("/v1/admin/keys", response_model=list[ApiKeyListItem])
async def list_api_keys(
    auth: AuthResult = Depends(require_permission("admin")),
) -> list[ApiKeyListItem]:
    """Expose non-sensitive metadata for all provisioned keys."""
    manager = _get_auth_manager()
    keys = await manager.list_keys(tenant_id=auth.tenant_id)
    return [
        ApiKeyListItem(
            id=str(k.id),
            name=k.name,
            prefix=k.key_prefix,
            tenant_id=k.tenant_id,
            permissions=k.permissions,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used=k.last_used,
        )
        for k in keys
    ]


# ─── Handoff & Continuity ───────────────────────────────────────────


@router.post("/v1/handoff")
async def generate_handoff_context(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
    auth: AuthResult = Depends(require_permission("read")),
) -> dict:
    """Manifest a session handoff artifact with hot context and recent episodes.

    Used for transferring agentic state between platforms (macOS -> Web).
    """
    from cortex.extensions.agents.handoff import generate_handoff, save_handoff

    lang = _get_lang(request)

    try:
        body = await request.json()
    except (ValueError, TypeError):
        body = {}

    session_meta = body.get("session") if isinstance(body, dict) else None
    try:
        data = await generate_handoff(engine, session_meta=session_meta)
        save_handoff(data)
        logger.info("Handoff generated: keys=%d", len(data))
        return data
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        logger.error("Handoff failure: %s", exc)
        SelfHealingHook.trigger(exc, {"endpoint": "generate_handoff_context"})
        raise HTTPException(status_code=500, detail=get_trans("error_unexpected", lang)) from None
