"""
Bitácora JSONL física. Evita las pérdidas estocásticas de estado post-reinicio guardando heartbeats y resultados de acciones.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("ouroboros.memory")
DATA_DIR = Path("/app/data") if Path("/app").exists() else Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def save_heartbeat(state: dict):
    try:
        with open(DATA_DIR / "heartbeats.jsonl", "a") as f:
            f.write(json.dumps(state) + "\\n")
    except Exception as e:
        logger.error(f"Failed to save heartbeat: {e}")

def save_memory(state: dict, plan: dict, result: str, outcome: str):
    record = {
        "state": state,
        "plan": plan,
        "result": result,
        "outcome": outcome
    }
    try:
        with open(DATA_DIR / "actions.jsonl", "a") as f:
            f.write(json.dumps(record) + "\\n")
        logger.info(f"Action memory saved: {outcome}")
    except Exception as e:
        logger.error(f"Failed to save action memory: {e}")

def get_recent_history(limit: int = 50) -> list:
    history = []
    file_path = DATA_DIR / "heartbeats.jsonl"
    if file_path.exists():
        with open(file_path, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return history

def get_recent_actions(limit: int = 20) -> list:
    actions = []
    file_path = DATA_DIR / "actions.jsonl"
    if file_path.exists():
        with open(file_path, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    actions.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return actions
