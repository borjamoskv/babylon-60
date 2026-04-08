"""CORTEX v5.0 - Search Router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, Query

from cortex.api.deps import get_public_memory_service
from cortex.auth import require_permission
from cortex.types.models import SearchRequest, SearchResult

__all__ = ["search_facts", "search_facts_get"]

router = APIRouter(tags=["search"])

if TYPE_CHECKING:
    from cortex.auth import AuthResult
    from cortex.services.public_memory import PublicMemoryService


@router.post("/v1/search", response_model=list[SearchResult])
async def search_facts(
    req: SearchRequest,
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[SearchResult]:
    """Semantic + Graph-RAG search across facts (scoped to tenant)."""
    return await service.search(
        query=req.query,
        top_k=req.k,
        project=req.project,
        tenant_id=auth.tenant_id,
        as_of=req.as_of,
        fact_type=req.fact_type,
        tags=req.tags,
        graph_depth=req.graph_depth,
        include_graph=req.include_graph,
        preserve_null_filters=True,
    )


@router.get("/v1/search", response_model=list[SearchResult])
async def search_facts_get(
    query: str = Query(..., max_length=1024),
    k: int = Query(5, ge=1, le=50),
    project: Optional[str] = Query(None, max_length=100),
    as_of: Optional[str] = None,
    fact_type: Optional[str] = None,
    tags: list[str] | None = Query(None),
    graph_depth: int = Query(0, ge=0, le=5),
    include_graph: bool = Query(False),
    auth: AuthResult = Depends(require_permission("read")),
    service: PublicMemoryService = Depends(get_public_memory_service),
) -> list[SearchResult]:
    """Semantic + Graph-RAG search via GET (scoped to tenant)."""
    return await service.search(
        query=query,
        top_k=k,
        project=project,
        tenant_id=auth.tenant_id,
        as_of=as_of,
        fact_type=fact_type,
        tags=tags,
        graph_depth=graph_depth,
        include_graph=include_graph,
        preserve_null_filters=True,
    )
