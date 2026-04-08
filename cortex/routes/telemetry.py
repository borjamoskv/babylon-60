from __future__ import annotations

"""
Sovereign Telemetry Routes (AST Oracle WebSocket API)
Exposes realtime stream of code mutations detected by AST Oracle.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from cortex.api.deps import get_async_engine
from cortex.crypto import get_default_encrypter, load_json_dict

if TYPE_CHECKING:
    from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("cortex.api.telemetry")
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


async def query_new_facts(
    engine: AsyncCortexEngine, last_id: int, fact_type: str
) -> tuple[int, list[dict[str, Any]]]:
    """Queries for new facts of specific type since last_id."""
    async with engine.session() as conn:
        async with conn.execute("PRAGMA table_info(facts)") as cursor:
            columns = {str(row[1]) for row in await cursor.fetchall()}

        meta_col = "metadata" if "metadata" in columns else "meta" if "meta" in columns else None
        select_meta = meta_col if meta_col is not None else "NULL"
        select_tenant = "tenant_id" if "tenant_id" in columns else "'default'"
        sql = (
            f"SELECT id, content, {select_meta}, {select_tenant} "
            "FROM facts "
            "WHERE fact_type = ? AND id > ? "
            "ORDER BY id ASC"
        )
        cursor = await conn.execute(sql, (fact_type, last_id))
        rows = await cursor.fetchall()

        results = []
        max_id = last_id
        encrypter = get_default_encrypter()
        for row in rows:
            fact_id, content_raw, meta_raw, tenant_id = row
            tenant = tenant_id or "default"
            content = content_raw
            if content_raw and str(content_raw).startswith(encrypter.PREFIX):
                try:
                    content = encrypter.decrypt_str(content_raw, tenant_id=tenant)
                except (RuntimeError, ValueError, TypeError, OSError):
                    content = content_raw
            meta = load_json_dict(meta_raw, tenant_id=tenant)
            results.append({"fact_id": fact_id, "content": content, "meta": meta})
            if fact_id > max_id:
                max_id = fact_id
        return max_id, results


@router.websocket("/ast-oracle")
async def ast_oracle_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime AST mutations to the Sovereign Web interface.
    """
    await websocket.accept()
    logger.info("👁️ Holographic Interface connected to AST Oracle.")

    # We want to get the last known ID first so we only send *new* mutations
    # But for a slicker demo upon connection, we can fetch the last 10
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT MAX(id) FROM facts")
        row = await cursor.fetchone()
        last_id = (row[0] or 0) - 100  # look back a bit  # type: ignore[reportOptionalSubscript]
    if last_id < 0:
        last_id = 0

    try:
        while True:
            new_max, mutations = await query_new_facts(engine, last_id, "human_mutation")
            for mut in mutations:
                await websocket.send_json({"event": "human_mutation", "data": mut})
            last_id = new_max
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("Holographic Interface disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("AST Oracle WS Error: %s", e)


@router.websocket("/fiat-stream")
async def fiat_stream_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime financial transactions.
    """
    await websocket.accept()
    logger.info("💰 Financial Telemetry connected to Fiat Oracle.")

    # Fetch last known ID
    async with engine.session() as conn:
        async with conn.execute(
            "SELECT MAX(id) FROM facts WHERE fact_type = 'fiat_transaction'"
        ) as cursor:
            row = await cursor.fetchone()
            last_id = row[0] or 0  # type: ignore[reportOptionalSubscript]

    try:
        while True:
            new_max, txs = await query_new_facts(engine, last_id, "fiat_transaction")
            for tx in txs:
                await websocket.send_json({"event": "fiat_transaction", "data": tx})
            last_id = new_max
            await asyncio.sleep(1.0)  # Slower poll for financial updates
    except WebSocketDisconnect:
        logger.info("Financial Telemetry disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Fiat Stream WS Error: %s", e)
