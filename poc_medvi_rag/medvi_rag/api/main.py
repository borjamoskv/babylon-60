from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from medvi_rag.orchestrator.medvi_engine import MedviEngine

app = FastAPI(title="Medvi-RAG Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
app.mount("/dashboard", StaticFiles(directory=frontend_path, html=True), name="frontend")

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../medvi_poc.db'))
engine = MedviEngine(DB_PATH)

class IntentRequest(BaseModel):
    intent: str

@app.post("/api/intent")
def process_intent(req: IntentRequest):
    try:
        result = engine.process_intent(req.intent)
        if result:
            return result
        else:
            raise HTTPException(status_code=400, detail="Failed to process intent. Check logs.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
