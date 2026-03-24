# Sovereign Swarm Architecture v5.0 (Ω-Persistence)

## Overview
The Swarm Architecture in CORTEX-Persist v0.3.1 has been consolidated into a recursive, exergy-driven system governed by the **Sovereign Ledger**. This architecture ensures that every agent recruitment, task sharding, and evolution cycle is cryptographically verifiable and iteratively optimized.

## Core Components

### 1. SwarmManager (The Orchestrator)
The central hub for governed actuators. It enforces:
- **Privacy Gates**: Mandatory content sanitization before external LLM dispatch.
- **Reputation Tracking**: Real-time exergy measurement per agent/actuator.
- **Recursive Audit**: `SwarmAuditor` monitors the entropy of the swarm state via the Ledger.

### 2. SwarmFactory (Iterative Recruitment)
Implements the **Law of the Cycle (Ω₃)**. Instead of one-shot recruitment, the factory operates in cycles:
- **Observe**: Identifies the gap between current and target exergy.
- **Act**: Enlists specialists from the `SkillRegistry` or forges JIT specialists.
- **Measure**: Calculates potential exergy yield.
- **Repeat**: Loops until the `exergy_target` (default 0.8) is satisfied.

### 3. Sovereign Ledger (Deterministic Ground Truth)
The cryptographic heart of the system.
- **Synchronous Persistence**: By design, `record_transaction` is a synchronous call to ensure atomic hash-chain continuity in high-frequency swarm environments.
- **Merkle Tree Integration**: Checkpoints (Ω-Singularity) consolidate transactions into immutable roots for v8 storage efficiency.

## Governance Laws (Applied)

- **Ω₁ (Byzantine Law)**: Every recruitment event crosses a deterministic boundary (The Ledger) before the squad is deployed.
- **Ω₃ (Cycle Law)**: Recruitment is an iterative process. Failed cycles result in "speculative voids" that trigger JIT forging rather than failure.
- **Ω₉ (Claim Law)**: Every exergy target must include a mechanical justification recorded in the transaction detail.

## Tactical Quadrants
The architecture supports multi-layered deployment:
- **Frontline**: High-impact tactical squads for immediate execution.
- **Support**: Auxiliary agents for research and background processing.
- **Shadow**: Specialized infiltration/forensic agents (e.g., Moltbook) for narrative operations.

---
*CORTEX-Persist | Sovereign Swarm v0.3.1-b1 | Approved: MOSKV-1*
