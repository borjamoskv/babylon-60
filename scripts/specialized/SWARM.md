# CORTEX Swarm Protocol (v1.1) — Lab Stage

The Swarm architecture in Phase 3 is constrained to a closed-loop laboratory. `Ouroboros-Strike` coordinates multiple local observers against the same Anvil endpoint, sharing VSA state and defensive replay artifacts without broadcasting transactions.

## 🏯 Node Architectures

| Role | Core Engine | Objective | Substrate |
|:---|:---:|:---|:---|
| **Hunter-Ω** | Rust (Alloy) | Pending-tx scanning & defensive replay planning | Local Anvil |
| **Oracle-§16** | Python (Guard) | Exergy invariant validation | Homeostasis |
| **Archivist-VSA** | Rust / FPGA HIL | Algebraic context persistence | Shared `state.vsa` |
| **Replayer-C4** | Rust | Trace emission only, no broadcast | Local trace directory |

## 🛰️ Coordination Layers

1. **Shared Endpoint**: All agents target the same `ws://127.0.0.1:8545` Anvil WebSocket.
2. **Global SDM Mesh**: Hypervectors are shared between Hunters to avoid redundant analysis of identical calldata patterns.
3. **Guarded Replay**: Every candidate must pass the Python guard before a local replay trace is written.

## 📊 Scalability Invariants

- **Latency**: bounded by local HIL and Anvil replay overhead.
- **Consistency**: file-lock protected writes for shared VSA state.
- **Safety**: `broadcast == disabled` under `lab_only`.

---
*"The swarm verifies, the hardware remembers."*
