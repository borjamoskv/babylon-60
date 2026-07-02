# [C5-REAL] Exergy-Maximized
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from babylon60.api.deps import get_async_engine
from babylon60.auth import require_permission
from babylon60.database.belief_store import BeliefStore
from babylon60.swarm.flujo_glorioso import DecaCoreOrchestrator

logger = logging.getLogger("flujo_glorioso_api")

router = APIRouter(prefix="/v1/flujo-glorioso", tags=["flujo_glorioso"])

class GenesisRequest(BaseModel):
    initial_idea: str = Field(..., description="La idea primigenia para inyectar en la génesis causal.")

@router.post("/genesis")
async def trigger_genesis(
    req: GenesisRequest,
    auth=Depends(require_permission("write")),
    engine=Depends(get_async_engine),
):
    """
    Despliega la iteración de génesis completa a lo largo del Orquestador Deca-Core.
    Transita desde la Concepción hasta el Despliegue.
    """
    # Initialize the BeliefStore using the pool attached to the engine
    store = BeliefStore(db=engine.db)
    orchestrator = DecaCoreOrchestrator(store)

    try:
        trajectory = await orchestrator.execute_genesis(req.initial_idea)
        
        # Serialize the generated BeliefObjects to JSON-friendly format
        return {
            "status": "success",
            "phases_completed": len(trajectory),
            "trajectory": [
                {
                    "id": b.belief_id,
                    "state": b.state.value,
                    "agent_id": b.provenance.signer_id,
                    "timestamp": b.provenance.created_at,
                    "content": b.proposition,
                }
                for b in trajectory
            ]
        }
    except Exception as e: # noqa: BLE001
        logger.error("Flujo Glorioso Genesis Failed: %s", e)
        raise HTTPException(status_code=500, detail="El orquestador colapsó termodinámicamente.") from e
