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
    "delete_memory",
    "get_memory",
    "list_memories",
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
