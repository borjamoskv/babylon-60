import asyncio
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from cortex.ledger.ledger_core import SovereignLedger

# Configuración básica de logging (C5-REAL standard)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CORTEX-Stress-Agent")

app = FastAPI(title="CORTEX Sovereign Stress Agent", version="0.3.0")

# Ledger Setup (Sidecar Database)
DB_PATH = "stress_agent_ledger.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
ledger = SovereignLedger(conn)

# Store in-memory cache for fast status retrieval
executions: dict[str, dict[str, Any]] = {}
execution_ids: list[str] = []
running_processes: dict[str, asyncio.subprocess.Process] = {}
active_connections: list[WebSocket] = []


class StressTrigger(BaseModel):
    authorization_key: str
    target_env: str = "local"
    intensity: int = 50  # Num agents by default


async def broadcast_log(message: str):
    """Envia un log a todos los clientes WebSocket conectados."""
    for connection in active_connections:
        try:
            await connection.send_text(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        except Exception:
            pass


async def execute_stress_test(execution_id: str, intensity: int):
    """
    Ejecuta el script de prueba de carga (test_autodidact_stress.py).
    Se ejecuta como subproceso para no bloquear el event loop (AX-046).
    """
    msg = f"Iniciando secuencia de estrés JIT con intensidad {intensity} (C5-REAL)..."
    logger.info(f"[{execution_id}] {msg}")
    await broadcast_log(f"EXEC_{execution_id[:8]}: {msg}")

    executions[execution_id]["status"] = "RUNNING"
    executions[execution_id]["started_at"] = datetime.now().isoformat()

    # Record start in Ledger
    ledger.record_transaction(
        "stress-agent", "STRESS_START", {"execution_id": execution_id, "intensity": intensity}
    )

    script_path = "test_autodidact_stress.py"
    if not os.path.exists(script_path):
        error_msg = "Script no encontrado"
        logger.error(f"[{execution_id}] {error_msg}: {script_path}. Abortando.")
        executions[execution_id]["status"] = "FAILED"
        executions[execution_id]["error"] = error_msg
        await broadcast_log(f"CRITICAL: {error_msg}")
        ledger.record_transaction(
            "stress-agent", "STRESS_ERROR", {"execution_id": execution_id, "error": error_msg}
        )
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CORTEX_INTENSITY": str(intensity)},
        )
        running_processes[execution_id] = proc

        # Stream stdout in real-time
        async def stream_output(stream, prefix):
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode("utf-8").rstrip()
                if prefix == "STDOUT":
                    executions[execution_id]["stdout"] = (
                        executions[execution_id].get("stdout", "") + line_str + "\n"
                    )
                else:
                    executions[execution_id]["stderr"] = (
                        executions[execution_id].get("stderr", "") + line_str + "\n"
                    )

                await broadcast_log(f"EXEC_{execution_id[:8]} {prefix}: {line_str}")

        await asyncio.gather(
            stream_output(proc.stdout, "STDOUT"), stream_output(proc.stderr, "STDERR"), proc.wait()
        )

        if execution_id in running_processes:
            del running_processes[execution_id]

        logger.info(
            f"[{execution_id}] Prueba de estrés completada. Código de salida: {proc.returncode}"
        )
        status = "COMPLETED" if proc.returncode == 0 else "FAILED_EXECUTION"
        if executions[execution_id].get("status") == "STOPPED":
            status = "STOPPED"

        executions[execution_id]["status"] = status
        executions[execution_id]["completed_at"] = datetime.now().isoformat()

        detail = {
            "execution_id": execution_id,
            "status": status,
            "exit_code": proc.returncode,
            "stdout_summary": executions[execution_id].get("stdout", "")[-500:],
            "stderr": executions[execution_id].get("stderr", ""),
        }

        ledger.record_transaction("stress-agent", "STRESS_COMPLETE", detail)

    except Exception as e:
        error_str = str(e)
        logger.error(f"[{execution_id}] Excepción crítica durante la ejecución: {error_str}")
        executions[execution_id]["status"] = "CRITICAL_ERROR"
        executions[execution_id]["error"] = error_str
        await broadcast_log(f"CRITICAL_ERROR: {error_str}")
        ledger.record_transaction(
            "stress-agent", "STRESS_CRITICAL", {"execution_id": execution_id, "error": error_str}
        )


DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CORTEX | Stress Agent Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0A0A0A; --surface: #121212; --primary: #2B3BE5;
            --accent: #FF3B30; --text: #E0E0E0; --text-dim: #888; --border: #222;
            --glow: 0 0 15px rgba(43, 59, 229, 0.4);
        }
        body {
            background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif;
            margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden;
        }
        header {
            padding: 1rem 2rem; border-bottom: 1px solid var(--border);
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(10, 10, 10, 0.9); backdrop-filter: blur(10px); z-index: 100;
        }
        h1 { font-size: 1rem; font-weight: 700; letter-spacing: 2px; margin: 0; }
        .status-dot {
            width: 8px; height: 8px; border-radius: 50%; background: #4CAF50;
            display: inline-block; margin-right: 8px; box-shadow: 0 0 10px #4CAF50;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        main { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 320px; border-right: 1px solid var(--border); padding: 1rem; overflow-y: auto; background: var(--surface); }
        .content { flex: 1; padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; }
        .card { background: var(--surface); border: 1px solid var(--border); padding: 1.2rem; border-radius: 4px; position: relative; transition: border-color 0.3s; }
        .card:hover { border-color: var(--primary); }
        .card h2 { font-size: 0.8rem; text-transform: uppercase; color: var(--text-dim); margin: 0 0 1rem 0; letter-spacing: 1px; }
        .btn {
            background: var(--primary); color: white; border: none; padding: 0.8rem 1.4rem;
            font-weight: 700; cursor: pointer; border-radius: 2px; text-transform: uppercase; font-size: 0.75rem;
            transition: all 0.2s; box-shadow: var(--glow);
        }
        .btn:hover { transform: translateY(-1px); filter: brightness(1.1); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
        .btn.stop { background: var(--accent); box-shadow: 0 0 15px rgba(255, 59, 48, 0.4); }
        .exec-item {
            padding: 0.8rem; border-bottom: 1px solid var(--border); cursor: pointer;
            display: flex; flex-direction: column; gap: 0.3rem; transition: background 0.2s;
        }
        .exec-item:hover { background: #1A1A1A; }
        .exec-item.active { border-left: 3px solid var(--primary); background: #151515; }
        .exec-item .id { font-family: 'JetBrains Mono'; font-size: 0.65rem; color: var(--text-dim); }
        .exec-item .meta { display: flex; justify-content: space-between; font-size: 0.7rem; font-weight: 700; }
        .status-QUEUED { color: #FFA500; } .status-RUNNING { color: var(--primary); }
        .status-COMPLETED { color: #4CAF50; } .status-FAILED, .status-STOPPED { color: var(--accent); }
        pre {
            background: #000; padding: 1rem; border-radius: 4px; font-family: 'JetBrains Mono';
            font-size: 0.75rem; border: 1px solid #111; white-space: pre-wrap; word-break: break-all;
            max-height: 300px; overflow-y: auto; color: #BBB;
        }
        .input-group { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1rem; }
        input { background: #000; border: 1px solid var(--border); padding: 0.6rem; color: white; font-family: 'JetBrains Mono'; font-size: 0.8rem; outline: none; }
        input:focus { border-color: var(--primary); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        #telemetry-box { height: 200px; }
    </style>
</head>
<body>
    <header>
        <h1>CORTEX // STRESS AGENT <span style="color: var(--text-dim);">v0.3.0</span></h1>
        <div><span class="status-dot"></span> SOVEREIGN_ONLINE</div>
    </header>
    <main>
        <div class="sidebar">
            <h2 style="font-size:0.8rem; color:var(--text-dim); margin-bottom:1rem;">HISTORY (Ω₄)</h2>
            <div id="history-list"></div>
        </div>
        <div class="content">
            <div class="card">
                <h2>TRIGGER COMMAND (Ω₈)</h2>
                <div class="grid">
                    <div class="input-group">
                        <label style="font-size:0.7rem;">Intensity (Agents)</label>
                        <input type="number" id="intensity" value="50">
                    </div>
                    <div class="input-group">
                        <label style="font-size:0.7rem;">Authorization Key</label>
                        <input type="password" id="auth_key" value="OUROBOROS-OMEGA-999">
                    </div>
                </div>
                <div style="display:flex; gap:1rem;">
                    <button class="btn" id="trigger-btn" onclick="triggerStress()">Execute Strike</button>
                    <button class="btn stop" id="stop-btn" onclick="stopStress()" style="display:none;">Terminate</button>
                </div>
            </div>
            <div id="details-panel" class="card" style="display:none;">
                <div style="display:flex; justify-content: space-between; margin-bottom:1rem;">
                    <h2 id="detail-title">DETAILS</h2>
                    <button class="btn" style="background:transparent; border:1px solid var(--border); padding:0.4rem 0.8rem;" onclick="closeDetails()">X</button>
                </div>
                <div id="detail-meta" class="grid" style="font-size:0.8rem; margin-bottom:1rem;"></div>
                <h3>STDOUT</h3><pre id="detail-stdout"></pre>
                <h3>STDERR</h3><pre id="detail-stderr"></pre>
            </div>
            <div class="card">
                <h2>REAL-TIME TELEMETRY (Ω₂)</h2>
                <pre id="telemetry-box"></pre>
            </div>
        </div>
    </main>
    <script>
        let activeId = null;
        let ws = null;

        function setupWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/telemetry`);
            ws.onmessage = (event) => {
                const box = document.getElementById('telemetry-box');
                box.innerText += event.data + '\n';
                box.scrollTop = box.scrollHeight;
            };
            ws.onclose = () => setTimeout(setupWebSocket, 2000);
        }

        async function triggerStress() {
            const intensity = document.getElementById('intensity').value;
            const auth = document.getElementById('auth_key').value;
            const btn = document.getElementById('trigger-btn');
            btn.disabled = true;
            try {
                const res = await fetch('/api/v1/trigger/stress', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ authorization_key: auth, intensity: parseInt(intensity) })
                });
                const data = await res.json();
                if (res.ok) {
                    activeId = data.execution_id;
                    refreshHistory();
                } else { alert(data.detail); }
            } finally { btn.disabled = false; }
        }

        async function stopStress() {
            if(!activeId) return;
            const res = await fetch(`/api/v1/trigger/stress/${activeId}/stop`, { method: 'POST' });
            if (res.ok) { refreshHistory(); }
        }

        async function refreshHistory() {
            const res = await fetch('/api/v1/trigger/stress');
            const data = await res.json();
            const list = document.getElementById('history-list');
            list.innerHTML = data.map(ex => `
                <div class="exec-item ${ex.id === activeId ? 'active' : ''}" onclick="loadDetails('${ex.id}')">
                    <div class="id">${ex.id.substring(0,8)}...</div>
                    <div class="meta">
                        <span>INT:${ex.intensity}</span>
                        <span class="status-${ex.status}">${ex.status}</span>
                    </div>
                </div>
            `).join('');

            // Show/Hide stop button
            const activeExec = data.find(ex => ex.id === activeId);
            const stopBtn = document.getElementById('stop-btn');
            if (activeExec && activeExec.status === 'RUNNING') {
                stopBtn.style.display = 'block';
            } else {
                stopBtn.style.display = 'none';
            }
        }

        async function loadDetails(id) {
            activeId = id;
            refreshHistory();
            const res = await fetch(`/api/v1/trigger/stress/${id}`);
            const data = await res.json();
            document.getElementById('details-panel').style.display = 'block';
            document.getElementById('detail-title').innerText = 'EXECUTION: ' + id.substring(0,13) + '...';
            document.getElementById('detail-meta').innerHTML = `
                <div><strong>STATUS:</strong> <span class="status-${data.status}">${data.status}</span></div>
                <div><strong>STARTED:</strong> ${data.started_at || '...'}</div>
            `;
            document.getElementById('detail-stdout').innerText = data.stdout || 'Processing...';
            document.getElementById('detail-stderr').innerText = data.stderr || 'No diagnostic errors.';
        }

        function closeDetails() { document.getElementById('details-panel').style.display = 'none'; activeId = null; refreshHistory(); }

        setupWebSocket();
        setInterval(refreshHistory, 3000);
        setInterval(() => { if(activeId) {
            // Only auto-reload details if still running
            const item = document.querySelector(`.exec-item.active .status-RUNNING`);
            if(item) loadDetails(activeId);
        } }, 2000);
        refreshHistory();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the Industrial Noir 2026 Dashboard."""
    return DASHBOARD_HTML


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        await websocket.send_text("TELEMETRY_CONNECTED: Sovereign Swarm Monitoring Active.")
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@app.post("/api/v1/trigger/stress")
async def trigger_stress_test(payload: StressTrigger, background_tasks: BackgroundTasks):
    """Endpoint para detonar la prueba de estrés de forma asíncrona."""
    if payload.authorization_key != "OUROBOROS-OMEGA-999":
        logger.warning("Intento de trigger rechazado: Autorización inválida.")
        raise HTTPException(status_code=401, detail="Byzantine Boundary: Unauthorized.")

    execution_id = str(uuid.uuid4())
    executions[execution_id] = {
        "id": execution_id,
        "status": "QUEUED",
        "intensity": payload.intensity,
        "target": payload.target_env,
        "started_at": None,
        "completed_at": None,
    }
    execution_ids.insert(0, execution_id)

    # Keep only last 100
    if len(execution_ids) > 100:
        old_id = execution_ids.pop()
        executions.pop(old_id, None)

    logger.info(f"[{execution_id}] Trigger recibido. Intensidad: {payload.intensity}")
    background_tasks.add_task(execute_stress_test, execution_id, payload.intensity)

    return {
        "status": "ACCEPTED",
        "execution_id": execution_id,
        "message": "CORTEX-Persist Stress Test sequence initiated (C5-REAL).",
    }


@app.post("/api/v1/trigger/stress/{execution_id}/stop")
async def stop_stress_test(execution_id: str):
    """Detiene una ejecución en curso."""
    if execution_id in running_processes:
        proc = running_processes[execution_id]
        proc.terminate()
        executions[execution_id]["status"] = "STOPPED"
        await broadcast_log(f"EXEC_{execution_id[:8]}: Terminated by user.")
        return {"status": "STOPPED"}
    raise HTTPException(status_code=404, detail="Execution not running or not found.")


@app.get("/api/v1/trigger/stress")
async def list_executions():
    """Lista todas las ejecuciones (ordenadas por recencia)."""
    return [executions[eid] for eid in execution_ids if eid in executions]


@app.get("/api/v1/trigger/stress/{execution_id}")
async def get_stress_status(execution_id: str):
    """Permite consultar el estado forense de una prueba en curso o finalizada."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution ID not found.")
    return executions[execution_id]


if __name__ == "__main__":
    import uvicorn

    logger.info("Inicializando CORTEX Stress Agent en puerto 8082...")
    uvicorn.run("stress_agent:app", host="127.0.0.1", port=8082, reload=False)
