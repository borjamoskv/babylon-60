from typing import Optional

"""
CORTEX v5.0 — Mission Orchestration Router.
"""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from cortex.api.deps import get_engine
from cortex.auth import require_permission
from cortex.engine import CortexEngine
from cortex.extensions.launchpad.main import MissionOrchestrator
from cortex.types.models import MissionLaunchRequest, MissionResponse

__all__ = ["launch_mission", "list_missions"]

logger = logging.getLogger("cortex.routes.missions")

router = APIRouter(prefix="/v1/missions", tags=["missions"])


@router.post("/launch", response_model=MissionResponse)
async def launch_mission(
    request: MissionLaunchRequest,
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("write")),
):
    """Launch a new swarm mission through the CORTEX Launchpad."""
    try:
        orchestrator = MissionOrchestrator(engine)
        result = orchestrator.launch(
            project=request.project,
            goal=request.goal,
            formation=request.formation,
            agents=request.agents,
        )
        return result
    except Exception as exc:
        logger.error("Mission launch failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Mission launch failed. Check server logs."},
        )


@router.get("/", response_model=list[dict])
async def list_missions(
    project: Optional[str] = Query(None),
    engine: CortexEngine = Depends(get_engine),
    _=Depends(require_permission("read")),
):
    """List recent mission intents and reports from the ledger."""
    try:
        orchestrator = MissionOrchestrator(engine)
        return orchestrator.list_missions(project=project)
    except Exception as exc:
        logger.error("Mission listing failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Could not retrieve missions."},
        )
