"""
Matriz de decisión basada en anomalías detectadas. Convierte el health_score y métricas aisladas en Playbooks accionables.
"""

import json
from pathlib import Path

def detect_anomalies(state: dict, health: dict) -> list:
    anomalies = []
    if state.get("cpu_pct", 0) > 90:
        anomalies.append("high_cpu")
    if state.get("ram_pct", 0) > 90:
        anomalies.append("high_ram")
    if health.get("health_score", 1.0) < 0.6:
        anomalies.append("low_health")
    if state.get("temperature_mc", 0) > 85000:
        anomalies.append("high_temp")
    return anomalies

DEFAULT_PLAYBOOKS = [
    {"name": "restart_container", "trigger": "high_cpu", "risk": "medium"},
    {"name": "flush_cache", "trigger": "high_ram", "risk": "low"},
    {"name": "throttle_cpu", "trigger": "high_temp", "risk": "low"},
    {"name": "reconnect_network", "trigger": "low_health", "risk": "medium"}
]

def load_learned_playbooks():
    """Phase 4: Basic learning heuristic retrieval"""
    try:
        path = Path("data/learning.json")
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_PLAYBOOKS

def generate_plan(anomalies: list, state: dict) -> dict | None:
    playbooks = load_learned_playbooks()
    
    # Priority resolution (first match)
    for anomaly in anomalies:
        for pb in playbooks:
            if pb.get("trigger") == anomaly:
                # Inject runtime context
                plan = pb.copy()
                plan["target"] = state.get("node_id", "local")
                return plan
    return None
