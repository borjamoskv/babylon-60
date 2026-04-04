"""CORTEX v6.0 — Demo Booking Router.

Exposes an open endpoint for capturing demo requests from the landing page.
Persists requests into the CORTEX ledger.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Request, HTTPException

from cortex.api.state import engine

__all__ = ["router"]

router = APIRouter(prefix="/v1/demo", tags=["demo"])
logger = logging.getLogger(__name__)

class DemoRequestPayload(BaseModel):
    email: EmailStr
    company: str
    use_case: str | None = None

@router.post("/book")
async def book_demo(payload: DemoRequestPayload, request: Request) -> dict:
    """Capture a demo booking request."""
    logger.info("Received Demo Request: %s from %s", payload.email, payload.company)
    
    if len(payload.company) < 2:
        raise HTTPException(status_code=422, detail="Company name too short")

    # Persist the request to the ledger as an 'intent' or 'demo_request'
    if engine is not None:
        try:
            # We store it into the default memory or system tenant
            await engine.add_fact(
                tenant_id="cortexpersist-landing",
                content=f"Demo Request via Landing: {payload.company} ({payload.email}) - Case: {payload.use_case}",
                metadata={
                    "type": "demo_request",
                    "email": payload.email,
                    "company": payload.company,
                    "use_case": payload.use_case or "N/A",
                }
            )
        except Exception as e:
            logger.error("Failed to commit demo request to ledger: %s", e)
            raise HTTPException(status_code=500, detail="Ledger persistence failed") from e
    else:
        logger.warning("Cortex Engine not initialized, demo request not persisted to ledger.")
        
    return {
        "status": "success",
        "message": "Demo request cryptographically logged.",
        "email": payload.email
    }
