"""
CORTEX v5.0 - Ledger Router.
Cryptographic integrity verification and checkpointing.
"""

import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.types.models import CheckpointResponse, LedgerReportResponse
from cortex.utils.i18n import get_trans

__all__ = [
    "LedgerError",
    "MerkleIntegrityError",
    "create_checkpoint",
    "get_ledger_status",
    "verify_ledger",
]


class LedgerError(Exception):
    """Base exception for ledger operations."""


class MerkleIntegrityError(LedgerError):
    """Raised when Merkle verification fails."""


logger = logging.getLogger("cortex.api.ledger")
router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


def _checkpoint_descriptor(value: object) -> tuple[int | None, str | None]:
    """Normalize legacy hash checkpoints and integer checkpoint IDs."""
    if value is None:
        return None, None
    if isinstance(value, int):
        return value, f"#{value}"
    return None, str(value)


@router.get("/status", response_model=LedgerReportResponse)
async def get_ledger_status(
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> LedgerReportResponse:
    """Check the cryptographic integrity of all ledgers (Tx and Votes)."""
    try:
        # 1. Verify Transaction Ledger
        tx_report = await engine.verify_ledger(auth.tenant_id)

        # 2. Verify Vote Ledger
        vote_report = await engine.verify_vote_ledger(auth.tenant_id)

        # Merge reports
        combined_valid = tx_report["valid"] and vote_report["valid"]
        combined_violations = tx_report["violations"] + vote_report["violations"]

        if not combined_valid:
            logger.error("Ledger violation detected! %s issues found.", len(combined_violations))

        return LedgerReportResponse(
            valid=combined_valid,
            violations=combined_violations,
            tx_checked=tx_report.get("tx_checked", 0),
            roots_checked=tx_report.get("roots_checked", 0),
            votes_checked=vote_report.get("votes_checked", 0),
            vote_checkpoints_checked=vote_report.get("checkpoints_checked", 0),
        )
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.exception("Ledger integrity check failed")
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(
            status_code=500,
            detail=get_trans("error_integrity_check_failed", lang).format(detail=str(e)),
        ) from None


@router.post("/checkpoint", response_model=CheckpointResponse)
async def create_checkpoint(
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> CheckpointResponse:
    """Manually trigger Merkle checkpoints for transactions and vote ledger."""
    try:
        cp_id = await engine.create_checkpoint(auth.tenant_id)
        vote_cp = None
        create_vote_checkpoint = cast(
            Callable[[str], Awaitable[object | None]] | None,
            getattr(engine, "create_vote_checkpoint", None),
        )
        if create_vote_checkpoint is not None:
            vote_cp = await create_vote_checkpoint(auth.tenant_id)

        checkpoint_id, checkpoint_ref = _checkpoint_descriptor(cp_id)
        vote_checkpoint_id, vote_checkpoint_ref = _checkpoint_descriptor(vote_cp)

        if cp_id or vote_cp:
            created_parts: list[str] = []
            if checkpoint_ref:
                created_parts.append(f"tx {checkpoint_ref}")
            if vote_checkpoint_ref:
                created_parts.append(f"vote {vote_checkpoint_ref}")
            return CheckpointResponse(
                checkpoint_id=checkpoint_id,
                checkpoint_ref=checkpoint_ref,
                vote_checkpoint_id=vote_checkpoint_id,
                vote_checkpoint_ref=vote_checkpoint_ref,
                message=f"Merkle checkpoints created successfully ({', '.join(created_parts)})",
            )
        else:
            return CheckpointResponse(
                checkpoint_id=None,
                checkpoint_ref=None,
                vote_checkpoint_id=None,
                vote_checkpoint_ref=None,
                message="No new ledger entries to checkpoint or batch size not reached",
                status="no_action",
            )
    except (sqlite3.Error, OSError, RuntimeError) as e:
        logger.exception("Merkle checkpoint creation failed")
        lang = request.headers.get("Accept-Language", "en")
        raise HTTPException(
            status_code=500, detail=get_trans("error_checkpoint_failed", lang).format(detail=str(e))
        ) from None


@router.get("/verify", response_model=LedgerReportResponse)
async def verify_ledger(
    request: Request,
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> LedgerReportResponse:
    """Alias for /status - performs full integrity verification."""
    return await get_ledger_status(request, auth, engine)
