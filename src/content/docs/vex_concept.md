---
title: "VEX — Verifiable Execution for Agents"
description: "CORTEX Persist Documentation — VEX — Concept for verifiable execution on top of CORTEX"
---


> *Concept: add a verifiable execution record on top of agent task runs.*

**Date:** 2026-03-02  
**Version:** 0.1.0-concept  
**Status:** Concept / Pre-Design  
**Author:** CORTEX Architecture Team  

---

## Executive Summary

VEX (Verifiable Execution) is a proposed extension to CORTEX that extends verification from agent memory into agent execution. It does not compete with model providers on inference quality. The goal is narrower: leave a stronger execution record around what an agent planned, ran, and returned.

Every action an agent takes during VEX execution would produce an **Execution Receipt**: a hash-chained, checkpointed record of what was executed and what result was observed.

---

## The Problem

Most current agent runners focus on planning, tool use, and convenience. They do not usually provide a built-in tamper-evident execution history.

> **Gap:** execution traces are usually logs, not verification artifacts.

| Runner | Memory | Execution Log | Integrity Proof | Consensus |
|:---|:---:|:---:|:---:|:---:|
| AutoGPT | Vector DB | JSON log | ❌ None | ❌ None |
| CrewAI | In-memory | stdout | ❌ None | ❌ None |
| OpenAI Operator | Ephemeral | API log | ❌ None | ❌ None |
| Gemini ADK | Context window | Session | ❌ None | ❌ None |
| **CORTEX VEX** | **L1+L2+L3 Tripartite** | **Hash-chained Ledger** | **✅ SHA-256 + Merkle** | **✅ WBFT** |

That gap matters more in regulated or review-heavy environments:

- **EU AI Act Article 12**: AI systems must maintain audit trails and logging capabilities.
- **SOC 2 Type II**: Requires demonstrable evidence that controls operated effectively.
- **ISO 42001**: Demands traceability of AI decision-making processes.

Many existing runners optimize for usability rather than traceability. CORTEX already addresses part of this problem on memory paths. VEX extends the same idea to execution.

---

## What CORTEX Already Has (The 80%)

| Component | Module | Role in VEX |
|:---|:---|:---|
| **Hash-Chained Ledger** | `engine/ledger.py` | Every execution step is a transaction |
| **Merkle Tree Checkpoints** | `engine/ledger.py` | Batch verification of execution history |
| **WBFT Consensus** | `consensus/` | Multi-agent agreement on execution outcomes |
| **Tripartite Memory** | `memory/` | L1 (working) + L2 (vector) + L3 (episodic) |
| **Privacy Shield** | `api/gate/` | 11-pattern secret detection at ingress |
| **Self-Healing Daemon** | `daemon/` | 13 monitors for system integrity |
| **ApotheosisEngine** | `engine/apotheosis.py` | Runtime analysis and proactive execution hooks |
| **Execution Loop Reference** | `sovereign_agent_manifesto.md` | Conceptual: `run_sovereign_agent()` |
| **Execution/Safety Model Reference** | `sovereign_agent_manifesto.md` | Reasoning, execution, and safety split |
| **MCP Server** | `mcp/` | Model Context Protocol integration |
| **REST API** | `api/` | FastAPI with RBAC, rate limiting |
| **CLI** | `cli/` | 90+ commands |
| **Circuit Breaker** | `proactive/circuit_breaker.py` | Failure isolation |
| **Compaction** | `compaction/` | Dedup + pruning |
| **OpenTelemetry** | `telemetry/` | Span tracing |

---

## What's Missing (The 20%)

### 1. Task Planner

A component that decomposes a high-level intent into a sequence of verifiable steps. Each step produces a `VerifiedStep` record in the ledger.

```python
@dataclass
class TaskPlan:
    """A decomposed task with verifiable steps."""
    task_id: str                    # Unique execution ID
    intent: str                     # Original human intent
    steps: list[PlannedStep]        # Ordered decomposition
    created_at: datetime
    plan_hash: str                  # SHA-256 of the plan itself

@dataclass
class PlannedStep:
    """A single planned step."""
    step_id: str
    description: str
    tool: str                       # Tool to invoke
    expected_outcome: str           # What constitutes success
    timeout_seconds: int
    tether_check: bool = True       # Verify against tether.md
```

### 2. Verified Execution Loop

The core loop that executes each step and produces hash-chained receipts.

```python
async def vex_execute(plan: TaskPlan) -> ExecutionReceipt:
    """Execute a plan with verification receipts."""
    receipt = ExecutionReceipt(task_id=plan.task_id)
    
    for step in plan.steps:
        # 1. TETHER CHECK (Brainstem)
        if not await tether_allows(step):
            receipt.abort(reason="tether_violation", step=step)
            break
        
        # 2. EXECUTE (Left Brain)
        result = await execute_step(step)
        
        # 3. RECORD (Hash-chain)
        tx = await ledger.log_transaction(
            project=plan.task_id,
            action=f"vex_step:{step.step_id}",
            detail={
                "tool": step.tool,
                "input_hash": hash(step.input),
                "output_hash": hash(result.output),
                "duration_ms": result.duration_ms,
                "success": result.success,
            }
        )
        
        # 4. PERSIST MEMORY (L3)
        await cortex.store(
            project=plan.task_id,
            content=result.summary,
            fact_type="execution_step",
            meta={"tx_hash": tx.hash, "step_id": step.step_id}
        )
        
        receipt.add_step(step, result, tx)
    
    # 5. MERKLE CHECKPOINT
    receipt.merkle_root = await ledger.create_merkle_checkpoint()
    
    # 6. OPTIONAL: CONSENSUS (if multi-agent)
    if plan.requires_consensus:
        receipt.consensus = await consensus.request_votes(receipt)
    
    return receipt
```

### 3. Execution Receipt

The output artifact — a verifiable proof of execution.

```python
@dataclass
class ExecutionReceipt:
    """Verifiable record that an agent executed a task."""
    task_id: str
    plan_hash: str                  # Hash of the original plan
    steps: list[StepResult]         # Ordered results
    merkle_root: str                # Root of the Merkle tree covering this execution
    total_duration_ms: int
    status: str                     # "completed" | "aborted" | "partial"
    consensus_score: float          # WBFT consensus (1.0 = unanimous)
    receipt_hash: str               # SHA-256 of the entire receipt
    
    def verify(self) -> bool:
        """Self-verification: recompute receipt_hash and compare."""
        ...
    
    def export_proof(self) -> dict:
        """Export as a portable JSON proof for third-party verification."""
        ...
```

---

## Architecture: VEX in the CORTEX Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        VEX LAYER (NEW)                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Task Planner │  │  VEX Loop    │  │  Execution Receipt   │  │
│  │  (Decompose)  │  │  (Execute)   │  │  (Proof Generator)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         └─────────────────┴──────────────────────┘              │
│                            │                                    │
├────────────────────────────┼────────────────────────────────────┤
│                    CORTEX ENGINE (Existing)                     │
│                            │                                    │
│  ┌──────────┐  ┌──────────┴──────────┐  ┌──────────────────┐  │
│  │  Memory   │  │  Ledger (Hash-Chain) │  │  Consensus (WBFT)│  │
│  │  L1+L2+L3 │  │  + Merkle Trees      │  │  + Reputation    │  │
│  └──────────┘  └─────────────────────┘  └──────────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │  Privacy  │  │  Daemon (13 monitors)│  │  Telemetry       │  │
│  │  Shield   │  │  Circuit Breaker     │  │  OpenTelemetry   │  │
│  └──────────┘  └─────────────────────┘  └──────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    INTERFACES (Planned)                         │
│  CLI (future VEX surface) │ REST API (/v1/vex/) │ MCP Server   │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Interface (Conceptual, Not Shipped)

There is no currently shipped dedicated VEX command family in the root CLI.

Treat the VEX interface as a design direction for a future execution surface rather than a current command set.

---

## API Interface

```
POST /v1/vex/run          — Submit a task for verified execution
GET  /v1/vex/{task_id}    — Get execution status + receipt
POST /v1/vex/verify       — Verify a receipt (third-party)
GET  /v1/vex/history      — List executions with filters
```

---

## Positioning

### What VEX Is NOT

- ❌ Not a new LLM (uses any LLM via configurable backend)
- ❌ Not a prompt engineering framework
- ❌ Not a RAG pipeline
- ❌ Not a chatbot builder

### What VEX IS

- ✅ A concept for adding **tamper-evident execution records**
- ✅ A way to extend CORTEX verification from memory into task execution
- ✅ Built on existing CORTEX primitives such as ledgering, checkpoints, and consensus
- ✅ Designed to support **Article 12-style traceability controls** when paired with deployment-specific governance
- ✅ Compatible with **any LLM backend** (Gemini, Claude, GPT, local models)

### Market Category

**Verifiable Agent Infrastructure** — the idea is to provide a verification layer around execution, not to replace the model, planner, or tool runtime itself.

---

## One-Liner

> **VEX: execution receipts for agent runs, built on top of CORTEX primitives.**

---

## Implementation Timeline

| Phase | Timeline | Deliverable |
|:---|:---|:---|
| **Phase 0** (current) | Week 1 | Concept doc (this document) + validation |
| **Phase 1** | Week 2-3 | `cortex/vex/planner.py` + `cortex/vex/loop.py` + `cortex/vex/receipt.py` |
| **Phase 2** | Week 4 | Dedicated VEX CLI surface + basic tests |
| **Phase 3** | Week 5-6 | `/v1/vex/` API endpoints + third-party verification |
| **Phase 4** | Month 2+ | Multi-agent consensus on execution + external anchoring |

---

## Open Questions

1. **LLM Backend**: Should VEX be opinionated about which LLM to use, or provide a pluggable interface from day one?
2. **Step Granularity**: How fine-grained should steps be? (per-tool-call vs. per-subtask)
3. **Cost Model**: Should each VEX execution have a cost ceiling enforced by `tether.md`?
4. **External Anchoring**: When to introduce blockchain/timestamping anchoring for Merkle roots?
5. **Naming**: Is "VEX" the right name? Alternatives: CORTEX Execute, CORTEX Prove, CORTEX Audit.

---

## Axiom Derivation

```
DECISION: CORTEX Verifiable Execution (VEX) concept
DERIVATION: 
  Ω₀ (Self-Reference) — This document describes the next form of CORTEX; reading it executes it.
  Ω₂ (Entropic Asymmetry) — VEX reduces entropy: one system for both memory AND execution trust.
  Ω₃ (Byzantine Default) — No runner is trusted. VEX makes trust verifiable, not assumed.
  Ω₄ (Aesthetic Integrity) — A runner without proof is ugly = incomplete.
  Ω₆ (Zenón's Razor) — Conclusion hasn't mutated in 6 lenses. Time to document and build.
```

---

*Prepared for CORTEX Architecture Review | 2026-03-02*  
*Protocol: ULTRATHINK-INFINITE*  
*Standard: 130/100*
