# [C5-REAL] Exergy-Maximized
"""CORTEX Gateway - FastAPI REST Adapter.

Exposes the GatewayRouter as a set of REST endpoints.
These routes accept normalized GatewayRequests and return GatewayResponses.

Endpoints::

    POST /gateway/v1/store    - store a fact
    POST /gateway/v1/search   - semantic search
    POST /gateway/v1/recall   - recall project facts
    GET  /gateway/v1/status   - system status
    POST /gateway/v1/emit     - fire a notification event

Auth: reuses existing CORTEX API key mechanism (X-API-Key header).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

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


async def _dispatch_gateway(
    gateway: GatewayRouter,
    intent: GatewayIntent,
    project: str,
    payload: dict[str, Any],
    error_status: int = 422,
) -> dict[str, Any]:
    """Normalize and handle a Gateway request, returning the response dict."""
    req = GatewayRequest(
        intent=intent,
        project=project,
        payload=payload,
        source="rest",
    )
    resp = await gateway.handle(req)
    if not resp.ok:
        raise HTTPException(status_code=error_status, detail=resp.error)
    return resp.to_dict()


@router.post("/store")
async def gateway_store(
    body: StoreBody,
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Store a fact through the Gateway."""
    return await _dispatch_gateway(
        gateway,
        GatewayIntent.STORE,
        body.project,
        {
            "content": body.content,
            "type": body.fact_type,
            "tags": body.tags,
            "source": body.source,
        },
        error_status=422,
    )


@router.post("/search")
async def gateway_search(
    body: SearchBody,
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Semantic search through the Gateway."""
    return await _dispatch_gateway(
        gateway,
        GatewayIntent.SEARCH,
        body.project,
        {"query": body.query, "top_k": body.top_k},
        error_status=422,
    )


@router.post("/recall")
async def gateway_recall(
    body: RecallBody,
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Recall project facts through the Gateway."""
    return await _dispatch_gateway(
        gateway,
        GatewayIntent.RECALL,
        body.project,
        {},
        error_status=422,
    )


@router.get("/status")
async def gateway_status(
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """System status through the Gateway."""
    return await _dispatch_gateway(
        gateway,
        GatewayIntent.STATUS,
        "",
        {},
        error_status=500,
    )


@router.post("/emit")
async def gateway_emit(
    body: EmitBody,
    gateway: GatewayRouter = Depends(_get_router),
) -> dict:
    """Fire a notification event through the Gateway."""
    return await _dispatch_gateway(
        gateway,
        GatewayIntent.EMIT,
        body.project,
        {
            "severity": body.severity,
            "title": body.title,
            "body": body.body,
            "metadata": body.metadata,
        },
        error_status=500,
    )
