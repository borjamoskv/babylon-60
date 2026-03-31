"""CORTEX Gateway — FastAPI REST Adapter.

Exposes the GatewayRouter as a set of REST endpoints.
These routes accept normalized GatewayRequests and return GatewayResponses.

Endpoints::

    POST /gateway/v1/store    — store a fact
    POST /gateway/v1/search   — semantic search
    POST /gateway/v1/recall   — recall project facts
    GET  /gateway/v1/status   — system status
    POST /gateway/v1/emit     — fire a notification event

Auth: reuses existing CORTEX API key mechanism (Authorization: Bearer <api-key>).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from cortex.auth import AuthResult, require_permission
from cortex.gateway import GatewayIntent, GatewayRequest, GatewayRouter

logger = logging.getLogger("cortex.gateway.rest")

router = APIRouter(prefix="/gateway/v1", tags=["gateway:v1"])


# ─── Request schemas ─────────────────────────────────────────────────


class StoreBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=50_000)
    project: str = Field(default="default")
    fact_type: str = Field(default="knowledge")
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="api")


class SearchBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=2_000)
    project: str = Field(default="")
    top_k: int = Field(default=5, ge=1, le=20)


class RecallBody(BaseModel):
    project: str = Field(..., min_length=1)


class EmitBody(BaseModel):
    severity: str = Field(default="info")
    title: str = Field(..., min_length=1)
    body: str = Field(default="")
    project: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── Dependency: get gateway router ──────────────────────────────────


def _get_router(request: Request) -> GatewayRouter:
    """Build a GatewayRouter from app state for each request."""
    import cortex.api.state as api_state

    engine = getattr(api_state, "async_engine", None) or getattr(api_state, "engine", None)
    bus = getattr(api_state, "notification_bus", None)

    if engine is None:
        raise HTTPException(status_code=503, detail="CORTEX engine not initialized")

    return GatewayRouter(engine=engine, bus=bus)


# ─── Routes ──────────────────────────────────────────────────────────


@router.post("/store")
async def gateway_store(
    body: StoreBody,
    auth: AuthResult = Depends(require_permission("write")),
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Store a fact through the Gateway."""
    req = GatewayRequest(
        intent=GatewayIntent.STORE,
        project=body.project,
        payload={
            "content": body.content,
            "type": body.fact_type,
            "tags": body.tags,
            "source": body.source,
        },
        tenant_id=auth.tenant_id,
        source="rest",
        caller_id=auth.key_name or auth.tenant_id,
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=422, detail=resp.error)
    return resp.to_dict()


@router.post("/search")
async def gateway_search(
    body: SearchBody,
    auth: AuthResult = Depends(require_permission("read")),
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Semantic search through the Gateway."""
    req = GatewayRequest(
        intent=GatewayIntent.SEARCH,
        project=body.project,
        payload={"query": body.query, "top_k": body.top_k},
        tenant_id=auth.tenant_id,
        source="rest",
        caller_id=auth.key_name or auth.tenant_id,
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=422, detail=resp.error)
    return resp.to_dict()


@router.post("/recall")
async def gateway_recall(
    body: RecallBody,
    auth: AuthResult = Depends(require_permission("read")),
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Recall project facts through the Gateway."""
    req = GatewayRequest(
        intent=GatewayIntent.RECALL,
        project=body.project,
        payload={},
        tenant_id=auth.tenant_id,
        source="rest",
        caller_id=auth.key_name or auth.tenant_id,
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=422, detail=resp.error)
    return resp.to_dict()


@router.get("/status")
async def gateway_status(
    auth: AuthResult = Depends(require_permission("read")),
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """System status through the Gateway."""
    req = GatewayRequest(
        intent=GatewayIntent.STATUS,
        payload={},
        tenant_id=auth.tenant_id,
        source="rest",
        caller_id=auth.key_name or auth.tenant_id,
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.error)
    return resp.to_dict()


@router.post("/emit")
async def gateway_emit(
    body: EmitBody,
    auth: AuthResult = Depends(require_permission("write")),
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Fire a notification event through the Gateway."""
    req = GatewayRequest(
        intent=GatewayIntent.EMIT,
        project=body.project,
        payload={
            "severity": body.severity,
            "title": body.title,
            "body": body.body,
            "metadata": body.metadata,
        },
        tenant_id=auth.tenant_id,
        source="rest",
        caller_id=auth.key_name or auth.tenant_id,
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=resp.error)
    return resp.to_dict()
