"""CORTEX Runtime API routes.

Provides /v1/runtime/health, /v1/runtime/boot_recovery
"""

from fastapi import APIRouter, HTTPException, Request

from cortex.extensions.health.reporting import build_runtime_health_payload
from cortex.types.models import RecoveryReport, RuntimeHealthResponse

router = APIRouter(prefix="/v1/runtime", tags=["runtime"])


@router.get("/health", response_model=RuntimeHealthResponse)
async def get_health(request: Request) -> RuntimeHealthResponse:
    """Retrieve runtime health report."""
    engine = getattr(request.app.state, "engine", None)
    db_path = str(getattr(engine, "_db_path", "")) if engine else ""
    return RuntimeHealthResponse.model_validate(build_runtime_health_payload(db_path))


@router.get("/boot_recovery", response_model=RecoveryReport)
async def get_boot_recovery(request: Request) -> RecoveryReport:
    """Get the memory recovery report generated during boot."""
    engine = getattr(request.app.state, "engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not available")

    report = getattr(engine, "recovery_report", None)
    if not report:
        # Default empty report if no recovery happened
        return RecoveryReport(
            status="clean", recovered_items=0, failed_items=0, last_checkpoint_id=None, warnings=[]
        )
    return report
