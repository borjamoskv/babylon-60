"""
CORTEX v5.0 — Daemon Router.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from cortex.auth import AuthResult, require_auth
from cortex.utils.i18n import get_trans

__all__ = ["daemon_status"]

router = APIRouter(tags=["daemon"])


@router.get("/v1/daemon/status")
def daemon_status(request: Request, auth: AuthResult = Depends(require_auth)) -> dict:
    """Get last daemon watchdog check results."""
    from cortex.extensions.daemon import MoskvDaemon

    lang = request.headers.get("Accept-Language", "en")
    if "admin" not in auth.permissions:
        raise HTTPException(
            status_code=403,
            detail=get_trans("error_missing_permission", lang).format(permission="admin"),
        )

    status = MoskvDaemon.load_status()
    if not status:
        return {"status": "no_data", "message": get_trans("error_daemon_no_data", lang)}
    return status
