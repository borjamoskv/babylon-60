"""Compatibility router for the legacy `/v1/memories` API surface.

This module preserves the public "memories" vocabulary while delegating
behavior to the canonical facts/search handlers.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from cortex.api.deps import get_public_memory_service
from cortex.auth import require_permission
from cortex.engine.storage_guard import GuardViolation

__all__ = [
    "batch_store",
    "execute_continual_memory",
    "continual_memory_status",
    "delete_memory",
    "forget_continual_memory",
    "get_memory",
    "list_memories",
    "plan_continual_memory",
    "search_memories",
    "store_memory",
    "verify_memories",
]

router = APIRouter(prefix="/v1/memories", tags=["memories"])

if TYPE_CHECKING:
    from cortex.auth import AuthResult
    from cortex.services.public_memory import PublicMemoryService


# ─── Request / Response Models ───────────────────────────────────────


class StoreMemoryRequest(BaseModel):
    """Request to store a memory."""

    project: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=32_768)
    type: str = Field("knowledge", description="knowledge, decision, error, etc.")
    tags: list[str] = Field(default_factory=list, max_length=20)
    source: Optional[str] = Field(None, description="Origin (e.g., 'agent:my-bot')")
    metadata: Optional[dict[str, Any]] = Field(None)
    parent_decision_id: Optional[int] = Field(
        None,
        description="Causal parent fact ID for chain tracking",
    )


class MemoryResponse(BaseModel):
    """A single memory in the response."""

    id: int
    project: str
    content: str
    type: str
    tags: list[str]
    confidence: str = "C3"
    source: Optional[str] = None
    parent_decision_id: Optional[int] = None
    created_at: str
    updated_at: str
    hash: Optional[str] = None
    score: Optional[float] = None


class SearchMemoryRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, max_length=1024, description="Natural language query")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    project: Optional[str] = Field(None, description="Filter by project")
    tags: Optional[list[str]] = Field(None, description="Filter by tags")
    as_of: Optional[str] = Field(None, description="Temporal filter (ISO timestamp)")


class BatchStoreRequest(BaseModel):
    """Batch store request."""

    memories: list[StoreMemoryRequest] = Field(..., min_length=1, max_length=100)


class ContinualPlanRequest(BaseModel):
    """Request to plan an adapter-only continual-learning update."""

    domain: str = Field(..., min_length=1, max_length=128)
    policy_violation: bool = False


class ContinualForgetRequest(BaseModel):
    """Request selective forgetting from the continual-learning sidecar."""

    user_id: str = Field(..., min_length=1, max_length=256)
    query: str = Field(..., min_length=1, max_length=2048)


class ContinualExecuteRequest(BaseModel):
    """Request to execute a continual-learning micro-update through a configured backend."""

    domain: str = Field(..., min_length=1, max_length=128)
    policy_violation: bool = False
    critical_domains: list[str] = Field(default_factory=list, max_length=32)


def _to_memory_response(value: BaseModel | dict[str, Any]) -> MemoryResponse:
    data = value.model_dump() if isinstance(value, BaseModel) else value
    memory_id = data.get("id", data.get("fact_id"))
    if memory_id is None:
        raise HTTPException(status_code=500, detail="Memory response missing id")

    return MemoryResponse(
        id=int(memory_id),
        project=str(data.get("project", "")),
        content=str(data.get("content", "")),
        type=str(data.get("fact_type", data.get("type", "knowledge"))),
        tags=list(data.get("tags") or []),
        confidence=data.get("confidence", "C3"),
        source=data.get("source"),
        parent_decision_id=data.get("parent_decision_id"),
        created_at=str(data.get("created_at") or ""),
        updated_at=str(data.get("updated_at") or data.get("created_at") or ""),
        hash=data.get("hash"),
        score=data.get("score"),
    )


# ─── Endpoints ───────────────────────────────────────────────────────


@router.post("", response_model=dict)
async def store_memory(
    req: StoreMemoryRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Store a memory via the canonical facts write path."""
    try:
        stored = await service.store(
            project=req.project,
            content=req.content,
            tenant_id=auth.tenant_id,
            fact_type=req.type,
            tags=req.tags,
            source=req.source,
            meta=req.metadata or {},
            parent_decision_id=req.parent_decision_id,
        )
    except (ValueError, GuardViolation) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        raise HTTPException(status_code=500, detail="Failed to store memory") from None
    return {"id": stored.fact_id, "project": stored.project, "status": "stored"}


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    request: Request,
    project: str = Query(..., min_length=1, description="Project to list memories from"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[MemoryResponse]:
    """List memories via the canonical facts recall path."""
    _ = request
    facts = await service.recall_project(
        project=project,
        limit=limit,
        offset=offset,
        tenant_id=auth.tenant_id,
    )
    return [_to_memory_response(fact) for fact in facts]


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    req: SearchMemoryRequest,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[MemoryResponse]:
    """Semantic search across memories via the canonical search handler."""
    results = await service.search(
        query=req.query,
        top_k=req.k,
        project=req.project,
        tenant_id=auth.tenant_id,
        as_of=req.as_of,
        tags=req.tags,
        preserve_null_filters=True,
    )
    return [_to_memory_response(result) for result in results]


@router.post("/batch", response_model=dict)
async def batch_store(
    req: BatchStoreRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Batch store memories via the canonical facts batch handler."""
    payload = [
        {
            "project": memory.project,
            "content": memory.content,
            "tenant_id": auth.tenant_id,
            "fact_type": memory.type,
            "tags": memory.tags,
            "source": memory.source,
            "meta": memory.metadata or {},
            "parent_decision_id": memory.parent_decision_id,
        }
        for memory in req.memories
    ]
    try:
        ids = await service.batch_store(payload)
    except (ValueError, GuardViolation) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (sqlite3.Error, OSError, RuntimeError):
        raise HTTPException(status_code=500, detail="Failed to batch store memories") from None
    return {
        "stored": len(ids),
        "ids": ids,
        "errors": [],
        "total_requested": len(req.memories),
    }


@router.get("/verify", response_model=dict)
async def verify_memories(
    request: Request,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Verify integrity via the canonical ledger verification handler."""
    _ = request
    _ = auth
    return await service.verify_ledger()


@router.get("/continual/status", response_model=dict)
async def continual_memory_status(
    domain: Optional[str] = Query(
        None, min_length=1, description="Optional continual-learning domain"
    ),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Return tenant-scoped continual-learning status for the legacy memories surface."""
    try:
        return await service.continual_learning_status(
            tenant_id=auth.tenant_id,
            domain=domain,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/continual/plan", response_model=dict)
async def plan_continual_memory(
    req: ContinualPlanRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Plan a tenant-scoped continual-learning micro-update."""
    try:
        plan = await service.plan_continual_update(
            tenant_id=auth.tenant_id,
            domain=req.domain,
            policy_violation=req.policy_violation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (OSError, RuntimeError, TypeError):
        raise HTTPException(
            status_code=500, detail="Failed to plan continual learning update"
        ) from None

    if plan is None:
        raise HTTPException(status_code=409, detail="Continual learning sidecar is disabled")
    return plan


@router.post("/continual/forget", response_model=dict)
async def forget_continual_memory(
    req: ContinualForgetRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Delete replay traces and queue clean replay for continual-learning state."""
    try:
        result = await service.forget_continual_memory(
            tenant_id=auth.tenant_id,
            user_id=req.user_id,
            query=req.query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (OSError, RuntimeError, TypeError):
        raise HTTPException(status_code=500, detail="Failed to forget continual memory") from None

    if result is None:
        raise HTTPException(status_code=409, detail="Continual learning sidecar is disabled")
    return result


@router.post("/continual/execute", response_model=dict)
async def execute_continual_memory(
    req: ContinualExecuteRequest,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Execute a continual-learning update when a backend is configured."""
    try:
        result = await service.execute_continual_update(
            tenant_id=auth.tenant_id,
            domain=req.domain,
            policy_violation=req.policy_violation,
            critical_domains=req.critical_domains,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (OSError, RuntimeError, TypeError):
        raise HTTPException(
            status_code=500, detail="Failed to execute continual learning update"
        ) from None

    if result is None:
        raise HTTPException(
            status_code=409,
            detail="Continual learning sidecar or training backend is disabled",
        )
    return result


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: int,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> MemoryResponse:
    """Get a single memory via the canonical fact-by-id handler."""
    fact = await service.get_fact(memory_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found")
    return _to_memory_response(fact)


@router.delete("/{memory_id}", response_model=dict)
async def delete_memory(
    memory_id: int,
    request: Request,
    auth: AuthResult = Depends(require_permission("write")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> dict:
    """Delete (soft-deprecate) a memory via the canonical facts handler."""
    _ = request
    fact = await service.get_fact_record(memory_id, tenant_id=auth.tenant_id)
    if not fact:
        raise HTTPException(status_code=404, detail=f"Memory #{memory_id} not found")

    success = await service.deprecate(memory_id, reason="api_deleted")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")
    return {"id": memory_id, "status": "deleted"}


@router.get("/{memory_id}/chain", response_model=list[dict])
async def get_causal_chain(
    memory_id: int,
    direction: str = Query("down", description="'up' or 'down'"),
    max_depth: int = Query(10, ge=1, le=100),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[dict]:
    """Get the causal chain for a memory via the canonical facts handler."""
    return await service.causal_chain(
        fact_id=memory_id,
        direction=direction,
        max_depth=max_depth,
        tenant_id=auth.tenant_id,
    )
