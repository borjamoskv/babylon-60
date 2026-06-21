"""
CORTEX-PERSIST: Ouroboros Node Keeper MVP
Loop asíncrono y exposición del API REST de salud. Orquesta el ciclo de vida continuo cada 60s.
"""
import asyncio
import logging

import uvicorn
from fastapi import FastAPI

from cortex.extensions.ouroboros_mythos.ouroboros_loop import MythosOuroborosEngine

app = FastAPI(title="Ouroboros Node Keeper")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ouroboros")

# Sovereign Mythos Engine Instance
engine = MythosOuroborosEngine()

@app.get("/health")
def read_health():
    health_score = engine.meta_controller.health_score
    status = "healthy" if health_score >= 9850 else "degraded"
    return {
        "status": status,
        "health_score": health_score,
        "active_version": engine.meta_controller.active_version,
        "cycle_count": engine.state.cycle_count,
        "state_hash": hex(engine.state.state_hash),
        "identity_anchor": engine.state.identity_anchor.decode("utf-8")
    }

@app.get("/metrics")
def read_metrics():
    return {
        "total_microjoules": engine.exergy.total_microjoules,
        "current_exergy_score": engine.exergy.current_score(),
        "temperature_mc": engine.exergy._read_temperature_mc(),
    }

@app.get("/ledger")
def read_ledger():
    log_path = engine.ledger.log_path
    events = []
    import json
    import os
    if os.path.exists(log_path):
        try:
            with open(log_path) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read ledger: {e}")
    return {"log_path": log_path, "events": events}

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Ouroboros Mythos Engine background task...")
    asyncio.create_task(engine.run_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
