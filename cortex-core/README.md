# CORTEX-Core: V5 Sovereign Substrate

This directory contains the high-fidelity primitive layer of the CORTEX ecosystem. As of V5 (Sovereign Ontogeny), all processes satisfy the **Substrate Unification Axiom**.

## 🏗️ Architecture: The Central Pulse

The system operates as a unified telemetry membrane synchronized via a shared SQLite substrate.

### 1. `cortex_daemon.py` (The Pulse Producer)
The main orchestrator. It manages:
- **SAGE COUNCIL**: Periodic deliberation and autonomous task dispatch.
- **MIRROR PROTOCOLS**: Self-audit cycles to maintain structural integrity.
- **Substrate Sync**: Emits `swarm_task` and `heartbeat` signals to the centralized bus.

### 2. `SignalBus` (The Shared Substrate)
Located at `~/.cortex/cortex.db`. This is the single source of truth for:
- **Telemetry**: Real-time events from all CORTEX services.
- **Ledger**: Cryptographically hashed decision lineage.
- **Signals Table**: Structured for cross-process atomic polling.

### 3. `x100_cortex_server.py` (The Aether Matrix Consumer)
A high-performance FastAPI/SSE backend that:
- **Streams Pulse**: Converts SignalBus events into Server-Sent Events (SSE) for UI dashboards.
- **Unifies State**: Provides a real-time HUD of the swarm's exergy and findings.

### 4. `ouroboros_engine.py` (The Strike Engine)
The security audit primitive. It executes deep-fuzzing and AST analysis, emitting `ledger_append` signals directly to the unified substrate when a vulnerability is crystallized.

## 🛠️ Diagnostics

To verify the system pulse manually, use the **Pulse-Check** utility:

```bash
# View the last 10 signals across the entire V5 ecosystem
python3 cortex-core/pulse_check.py
```

## ∴ Operational Seal
> All core modifications must preserve the **Canonical Path Resolution** at `cortex.config.DB_PATH`. Any deviation results in signal isolation and system blindness.
