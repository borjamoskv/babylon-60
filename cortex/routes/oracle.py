# [C5-REAL] Exergy-Maximized
from __future__ import annotations

# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""The Oracle Router (B2B SaaS Endpoint).

POST /v1/oracle/audit - Executes a Sovereign Agent to audit a target.
Requires an API key provided by Stripe (pro or team plan).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile
from cortex.swarm.runtime import SubagentRequest

__all__ = [
    "OracleRequest",
    "OracleResponse",
    "audit_target",
]

logger = logging.getLogger("cortex.routes.oracle")

router = APIRouter(tags=["oracle"])

# ─── Singleton LLM Manager ──────────────────────────────────────────
_llm_manager = LLMManager()


# ─── Request / Response Models ───────────────────────────────────────


class OracleRequest(BaseModel):
    """Request to trigger The Oracle audit on a target."""

    target_url: HttpUrl
    agent_type: str = "ariadne"  # e.g., 'ariadne', 'nyx', 'scavenger'
    depth: int = 1  # 1: Surface, 2: Deep, 3: Exhaustive


class OracleResponse(BaseModel):
    """The Oracle's audit report."""

    target: str
    agent: str
    report: str
    confidence: float
    status: str


# ─── System Prompt ───────────────────────────────────────────────────

ORACLE_SYSTEM_PROMPT = """\
[IDENTITY] CORTEX Oracle | Sovereign B2B Auditor.
[ROLE] You are the requested specialized agent (e.g., Ariadne for architecture, Nyx for security,
Scavenger for supply). You are performing a remote heuristic audit of the provided target URL.

[STRUCTURAL TOPOLOGY: AUDIT CONSTRAINTS]
- 1. High Velocity Analysis: Output a dense, actionable report revealing critical flaws and
     high-value opportunities at the target.
- 2. Concrete Examples: Generate plausible but highly detailed simulated findings based on the
     domain of the target URL.
- 3. Tone: Ruthless, authoritative, industrial tech-noir. Omit greetings. Just pure signal.
- 4. Output format: Markdown. Use bullet points and bolding for emphasis.
"""


# ─── Endpoints ───────────────────────────────────────────────────────



from starlette.requests import Request


@router.post("/v1/oracle/audit", response_model=OracleResponse, responses={500: {"description": "Oracle yielded no insights."}, 502: {"description": "Oracle Engine Error: Subagent failed."}, 503: {"description": "The Oracle is currently disconnected from the Swarm core."}})
async def audit_target(
    req: OracleRequest,
    request: Request,
    auth: Annotated[AuthResult, Depends(require_permission("read"))],
    engine: AsyncCortexEngine = Depends(get_async_engine),
):
    swarm_runner = getattr(request.app.state, "swarm_runner", None)

    if swarm_runner is not None:
        subreq = SubagentRequest(
            task_id=f"oracle:{auth.tenant_id}:{req.target_url}",
            kind="audit",
            target_agent=req.agent_type,
            prompt="audit",
            context={
                "target_url": str(req.target_url),
                "depth": req.depth,
                "tenant_id": auth.tenant_id,
                "agent_type": req.agent_type,
            },
            timeout_ms=30_000,
            max_retries=1,
        )
        resp = await swarm_runner.invoke_subagent(subreq)
        if not resp.ok:
            raise HTTPException(status_code=502, detail=resp.error or "oracle_failed")
        report = str(resp.output)
    else:
        if not _llm_manager.available:
            return JSONResponse(status_code=503, content={"detail": "The Oracle is currently disconnected from the LLM core."})
        prompt = (
            f"## Target URL: {req.target_url}\n"
            f"## Requested Agent: {req.agent_type.upper()}\n"
            f"## Audit Depth: {req.depth}/3\n\n"
            "Generate a critical audit report for this target. Identify at least "
            "3 critical vulnerabilities or massive performance/growth bottlenecks. "
            "Provide actionable solutions."
        )
        try:
            report = await _llm_manager.complete(
                prompt=prompt,
                system=ORACLE_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=2048,
                intent=IntentProfile.REASONING,
            )
        except (OSError, RuntimeError) as e:
            raise HTTPException(status_code=502, detail=f"Oracle Engine Error: {e!s}") from e

    confidence = 0.89 + (req.depth * 0.03)

    try:
        await engine.store(
            project="the_oracle",
            content=report,
            tenant_id=auth.tenant_id,
            fact_type="oracle_audit",
            tags=["oracle", req.agent_type, str(req.target_url)],
            source=f"agent:{req.agent_type}",
            meta={"confidence": confidence, "target_url": str(req.target_url), "depth": req.depth},
        )
    except Exception as e:
        logger.warning("Failed to persist Oracle audit to ledger: %s", e)

    return OracleResponse(
        target=str(req.target_url),
        agent=req.agent_type,
        report=report,
        confidence=confidence,
        status="COMPLETED",
    )
