import time

"""
Capa sensora (CPU, RAM, Disco) vía psutil. Aquí se inyectarían las llamadas directas a las APIs del nodo Inmunify/Grass.
"""
import psutil


async def collect_metrics() -> dict:
    return {
        "timestamp": int(time.time()),
        "node_id": "inmunify-node-01",
        "cpu_pct": psutil.cpu_percent(interval=1),
        "ram_pct": psutil.virtual_memory().percent,
        "disk_pct": psutil.disk_usage('/').percent,
        "latency_ms": 45,  # Mocked external call latency
        "rewards_24h": 3.42, # Mocked DB lookup
        "uptime_pct": 99.9 # Mocked API response
    }
