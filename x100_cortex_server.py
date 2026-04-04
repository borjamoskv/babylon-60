import asyncio
import time
import os
import json
import logging
import struct
import sys
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import uvicorn
import aiosqlite

# CORTEX V5 Pulse Integration
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import AsyncSignalBus

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] CORTEX-SERVER: %(message)s"
)
logger = logging.getLogger("cortex.server")

app = FastAPI(title="CORTEX-X100-SSE-ENGINE")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# --- SHARED STATE (Legacy/Hybrid) --- #
STATE = {
    "is_running": False,
    "cycle_count": 0,
    "global_yield": 0.0,
    "exergy_ratio": 1.0,
    "vectors": [
        {"id": 'bounty', "name": 'Code4rena Bounties', "yield": 0.0, "baseline": 2.5},
        {"id": 'mev', "name": 'LayerZero Fuzz', "yield": 0.0, "baseline": 1.2},
        {"id": 'millennium', "name": 'Riemann Singularities ($1M)', "yield": 0.0, "baseline": 1000.0},
    ],
    "logs": [],
    "agent_states": [0.0] * 10000 
}

# --- SOVEREIGN MEMBRANE REGISTRY --- #
@app.on_event("startup")
async def startup_event():
    # Initialize shared database connection
    app.state.db_conn = await aiosqlite.connect(DB_PATH)
    logger.info("Sovereign Memory Backend Connected: %s", DB_PATH)

@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "db_conn"):
        await app.state.db_conn.close()

# --- V5 SSE TELEMETRY PORT --- #
@app.get("/v1/events/stream")
async def sse_stream(request: Request):
    async def event_generator() -> AsyncGenerator[str, None]:
        bus = AsyncSignalBus(app.state.db_conn)
        consumer_id = f"dashboard_{int(time.time())}"
        logger.info("SSE: New consumer connected: %s", consumer_id)
        
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("SSE: Consumer disconnected: %s", consumer_id)
                    break
                    
                # Poll for new signals
                signals = await bus.poll(consumer=consumer_id, limit=20)
                for sig in signals:
                    event_data = {
                        "id": sig.id,
                        "event_type": sig.event_type,
                        "payload": sig.payload,
                        "source": sig.source,
                        "created_at": sig.created_at
                    }
                    yield f"event: {sig.event_type}\ndata: {json.dumps(event_data)}\n\n"
                
                # Keep-alive pulse
                if not signals:
                    yield ": ping\n\n"
                    
                await asyncio.sleep(1)
        except Exception as e:
            logger.error("SSE Stream Error: %s", e)
            
    return EventSourceResponse(event_generator())

# --- WEBSOCKET BINARY SWARM VISUALIZER --- #
class SwarmManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_binary(self, data: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except Exception:
                pass

swarm_manager = SwarmManager()

@app.websocket("/ws/swarm")
async def websocket_endpoint(websocket: WebSocket):
    await swarm_manager.connect(websocket)
    try:
        while True:
            # Heartbeat check
            await websocket.receive_text()
    except WebSocketDisconnect:
        swarm_manager.disconnect(websocket)

# --- LEGACY COMPATIBILITY ENDPOINTS --- #
@app.get("/stream")
async def legacy_stream(request: Request):
    """Proxy /stream to /v1/events/stream for older dashboard versions."""
    return await sse_stream(request)

if __name__ == "__main__":
    logger.info("Launching CORTEX Aether Matrix Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
