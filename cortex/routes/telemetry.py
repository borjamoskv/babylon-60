"""
Sovereign Telemetry Routes (AST Oracle WebSocket API)
Exposes realtime stream of code mutations detected by AST Oracle.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, WebSocketException, status

from cortex.api.deps import get_async_engine
from cortex.crypto import get_default_encrypter
from cortex.auth.manager import get_auth_manager
from cortex.auth.models import AuthResult
from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.utils.redaction import redact_text, redact_value

logger = logging.getLogger("cortex.api.telemetry")
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _decode_fact_content(raw_content: str | None, tenant_id: str) -> str:
    if not raw_content:
        return ""
    return get_default_encrypter().decrypt_str(raw_content, tenant_id=tenant_id) or ""


def _decode_fact_meta(meta_raw: str | None, tenant_id: str) -> dict[str, Any]:
    if not meta_raw:
        return {}

    if meta_raw.startswith("{"):
        try:
            return json.loads(meta_raw)
        except json.JSONDecodeError:
            return {}

    try:
        return get_default_encrypter().decrypt_json(meta_raw, tenant_id=tenant_id) or {}
    except ValueError:
        return {}


async def query_new_facts(
    engine: AsyncCortexEngine,
    tenant_id: str,
    last_id: int,
    fact_type: str,
) -> tuple[int, list[dict[str, Any]]]:
    """Queries for new facts of specific type since last_id."""
    async with engine.session() as conn:
        sql = """
            SELECT id, content, meta 
            FROM facts 
            WHERE fact_type = ? AND id > ? AND tenant_id = ?
            ORDER BY id ASC
        """
        cursor = await conn.execute(sql, (fact_type, last_id, tenant_id))
        rows = await cursor.fetchall()

        results = []
        max_id = last_id
        for row in rows:
            fact_id, content, meta_raw = row
            results.append(
                {
                    "fact_id": fact_id,
                    "content": redact_text(_decode_fact_content(content, tenant_id)),
                    "meta": redact_value(_decode_fact_meta(meta_raw, tenant_id)),
                }
            )
            if fact_id > max_id:
                max_id = fact_id
        return max_id, results


async def require_websocket_read_auth(websocket: WebSocket) -> AuthResult:
    """Authenticate websocket clients and require read permission before accept."""
    lang = websocket.headers.get("Accept-Language", "en")
    authorization = websocket.headers.get("Authorization")

    if not authorization:
        from cortex.utils.i18n import get_trans

        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=get_trans("error_missing_auth", lang),
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        from cortex.utils.i18n import get_trans

        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=get_trans("error_invalid_key_format", lang),
        )

    result = await get_auth_manager().authenticate_async(parts[1])
    if not result.authenticated:
        from cortex.utils.i18n import get_trans

        error_msg = get_trans("error_invalid_revoked_key", lang) if result.error else result.error
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=error_msg)

    if "read" not in result.permissions:
        from cortex.utils.i18n import get_trans

        detail = get_trans("error_missing_permission", lang).format(permission="read")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason=detail)

    from cortex.extensions.security.tenant import tenant_id_var

    tenant_id_var.set(result.tenant_id)
    return result


@router.websocket("/ast-oracle")
async def ast_oracle_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime AST mutations to the Sovereign Web interface.
    """
    auth = await require_websocket_read_auth(websocket)
    await websocket.accept()
    logger.info("👁️ Holographic Interface connected to AST Oracle.")

    # We want to get the last known ID first so we only send *new* mutations
    # But for a slicker demo upon connection, we can fetch the last 10
    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?",
            (auth.tenant_id, "human_mutation"),
        )
        row = await cursor.fetchone()
        last_id = (row[0] or 0) - 100  # look back a bit  # type: ignore[reportOptionalSubscript]
    if last_id < 0:
        last_id = 0

    try:
        while True:
            new_max, mutations = await query_new_facts(
                engine,
                auth.tenant_id,
                last_id,
                "human_mutation",
            )
            for mut in mutations:
                await websocket.send_json({"event": "human_mutation", "data": mut})
            last_id = new_max
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("Holographic Interface disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("AST Oracle WS Error: %s", redact_text(str(e)))


@router.websocket("/fiat-stream")
async def fiat_stream_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime financial transactions.
    """
    auth = await require_websocket_read_auth(websocket)
    await websocket.accept()
    logger.info("💰 Financial Telemetry connected to Fiat Oracle.")

    # Fetch last known ID
    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?",
            (auth.tenant_id, "fiat_transaction"),
        )
        row = await cursor.fetchone()
        last_id = row[0] or 0  # type: ignore[reportOptionalSubscript]

    try:
        while True:
            new_max, txs = await query_new_facts(
                engine,
                auth.tenant_id,
                last_id,
                "fiat_transaction",
            )
            for tx in txs:
                await websocket.send_json({"event": "fiat_transaction", "data": tx})
            last_id = new_max
            await asyncio.sleep(1.0)  # Slower poll for financial updates
    except WebSocketDisconnect:
        logger.info("Financial Telemetry disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Fiat Stream WS Error: %s", redact_text(str(e)))
