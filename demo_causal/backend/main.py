from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import init_db
from .engine import generate_10k_events, audit_chain, get_causal_chain, get_latest_events

app = FastAPI(title="CORTEX-PERSIST Causal Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/api/generate")
def generate_events():
    """Generates 10000 events"""
    count = generate_10k_events()
    return {"status": "success", "events_generated": count}

@app.get("/api/audit")
def audit():
    """Verifies the hash chain integrity"""
    return audit_chain()

@app.get("/api/causal_query/{event_id}")
def causal_query(event_id: int):
    """Returns the causal chain for a given event"""
    result = get_causal_chain(event_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/api/events")
def latest_events(limit: int = 50):
    return get_latest_events(limit)

@app.get("/api/status")
def status():
    audit_res = audit_chain()
    return {
        "status": "online",
        "events_loaded": audit_res["events"],
        "hash_integrity": audit_res["integrity"] == "valid",
        "last_event": {"id": audit_res["events"]}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
