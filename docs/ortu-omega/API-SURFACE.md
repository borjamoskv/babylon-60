# API-SURFACE.md — ORTU-Ω Phase 2

> **Program**: ORTU-Ω Forge · **Codename**: SORTU-Ω  
> **Input**: [PILLAR-MAP.md](PILLAR-MAP.md) · [REPOSITORY-CENSUS.md](REPOSITORY-CENSUS.md)  
> **Generated**: 2026-03-14

> **Historical note (2026-04-14):** this document describes a proposed target SDK surface from the ORTU-Ω design phase. The current repository treats `cortex-sdk/` as a legacy workspace, not as the primary supported Python package.

---

## 1. Design Rules

| Rule | Enforcement |
|:-----|:-----------|
| **No accidental internal exports** | Only types in this document are public. Everything else is `_private` |
| **Typed contracts** | Pydantic v2 models. No `dict[str, Any]` leaking across boundaries |
| **Versioned** | `/v1/` prefix. Breaking changes → `/v2/` |
| **Tenant-aware** | Every operation accepts `tenant_id`. Default = `"default"` |
| **Rejection > fallback** | Invalid input returns typed error, never silent degradation |
| **Deterministic failures** | Every error has a code, message, and category |
| **Idempotent reads** | `GET` operations are safe to retry |
| **Hash-sealed writes** | Every mutation returns `tx_hash` for verification |

---

## 2. Resource Models

### Core Resources

```python
class Fact(BaseModel):
    """Atomic unit of agent memory."""
    id: int
    project: str
    content: str
    fact_type: str                    # knowledge | decision | observation | error
    confidence: str                   # C1 (🔴) → C5 (🟢)
    source: str | None = None
    tags: list[str] = []
    hash: str                         # SHA-256 content hash
    tx_hash: str | None = None        # Transaction chain hash
    tenant_id: str = "default"
    consensus_score: float = 1.0
    is_tombstoned: bool = False
    created_at: datetime
    updated_at: datetime

class SearchResult(BaseModel):
    """Ranked retrieval result."""
    fact: Fact
    score: float                      # Relevance score [0.0, 1.0]
    match_type: str                   # hybrid | text | vector | graph
```

### Trust Resources

```python
class CausalTrace(BaseModel):
    """DAG of causal relationships between facts."""
    root_fact_id: int
    nodes: dict[int, TraceNode]       # fact_id → node
    edges: list[CausalEdge]
    depth: int
    total_nodes: int

class TraceNode(BaseModel):
    fact_id: int
    content_preview: str              # First 200 chars
    confidence: str
    taint_status: str                 # CLEAN | SUSPECT | TAINTED
    effective_confidence: str

class CausalEdge(BaseModel):
    parent_id: int
    child_id: int
    edge_type: str                    # causal | supersedes | contradicts

class VerificationResult(BaseModel):
    """Ledger integrity check."""
    valid: bool
    tx_checked: int
    roots_checked: int
    violations: list[Violation] = []

class Violation(BaseModel):
    location: str                     # tx_id or merkle_id
    violation_type: str               # chain_break | hash_mismatch | merkle_mismatch
    expected: str
    actual: str

class TaintReport(BaseModel):
    """Taint propagation result for a fact."""
    fact_id: int
    taint_status: str                 # CLEAN | SUSPECT | TAINTED
    effective_confidence: str
    tainted_ancestors: list[int] = []
    affected_descendants: list[int] = []
```

### Coordination Resources

```python
class Agent(BaseModel):
    """Registered agent in the coordination layer."""
    id: str                           # UUID
    name: str
    agent_type: str                   # ai | human | system
    reputation_score: float = 1.0
    is_active: bool = True
    tenant_id: str = "default"
    created_at: datetime

class VoteResult(BaseModel):
    """Result of a consensus vote."""
    fact_id: int
    agent_id: str
    vote: int                         # -1 | 0 | 1
    consensus_score: float            # Updated score after vote
    quorum_reached: bool

class ConsensusStatus(BaseModel):
    """Current consensus state for a fact or project."""
    fact_id: int | None = None
    project: str | None = None
    total_votes: int
    score: float
    status: str                       # verified | disputed | pending
    voters: list[str] = []            # agent_ids
```

### Compliance Resources

```python
class AuditReport(BaseModel):
    """EU AI Act Article 12 compliance report."""
    regulation: str = "EU AI Act (Regulation 2024/1689)"
    article: str = "12 — Record-Keeping"
    score: str                        # "5/5"
    status: str                       # COMPLIANT | NON_COMPLIANT
    checks: dict[str, ComplianceCheck]
    integrity: VerificationResult
    facts_summary: FactsSummary
    generated_at: datetime

class ComplianceCheck(BaseModel):
    description: str
    compliant: bool
    evidence: str
```

### Error Resources

```python
class TrustError(BaseModel):
    """Typed error returned by all rejection paths."""
    code: str                         # GUARD_CONTRADICTION | DEDUP_EXACT | ...
    message: str
    category: str                     # validation | guard | immune | integrity
    fact_id: int | None = None
    remediation: str | None = None    # Actionable hint

# Error codes
GUARD_CONTRADICTION    = "guard.contradiction"
GUARD_IMMUNE_BLOCK     = "guard.immune.block"
GUARD_IMMUNE_HOLD      = "guard.immune.hold"
GUARD_PRIVACY          = "guard.privacy"
DEDUP_EXACT            = "dedup.exact_match"
DEDUP_SEMANTIC         = "dedup.semantic_match"
VALIDATION_EMPTY       = "validation.empty_content"
VALIDATION_PROJECT     = "validation.invalid_project"
INTEGRITY_CHAIN_BREAK  = "integrity.chain_break"
INTEGRITY_HASH         = "integrity.hash_mismatch"
AGENT_NOT_FOUND        = "coordination.agent_not_found"
AGENT_INACTIVE         = "coordination.agent_inactive"
TAINT_BLOCKED          = "taint.write_blocked"
```

---

## 3. Operations

### 3.1 Memory (Pillar 1 + 4)

| Operation | Method | Path | Input | Output | Tier |
|:----------|:------:|:-----|:------|:-------|:-----|
| **Store** | `POST` | `/v1/facts` | `{project, content, fact_type?, tags?, source?, meta?}` | `StoreResponse` | Open |
| **Batch Store** | `POST` | `/v1/facts/batch` | `{memories: [{...}], max: 100}` | `{stored, ids, errors, total_requested}` | Open |
| **Get** | `GET` | `/v1/facts/{id}` | — | `Fact` | Open |
| **List** | `GET` | `/v1/facts` | `?limit=` | `Fact[]` | Open |
| **Search** | `POST` | `/v1/facts/search` | `{query, project?, k?, tags?, strategy?}` | `SearchResult[]` | Open |
| **Recall** | `GET` | `/v1/projects/{project}/facts` | `?limit=` | `Fact[]` | Open |
| **History** | `GET` | `/v1/facts/{id}/history` | — | `Fact[]` (versions) | Open |
| **Deprecate** | `DELETE` | `/v1/facts/{id}` | — | `{message, success}` | Open |

> `search` remains the query surface. Project-scoped recall is exposed separately through `GET /v1/projects/{project}/facts`.

### 3.2 Traceability (Pillar 2)

| Operation | Method | Path | Input | Output | Tier |
|:----------|:------:|:-----|:------|:-------|:-----|
| **Verify Ledger** | `GET` | `/v1/ledger/verify` | — | `VerificationResult` | Open |
| **Causal Chain** | `GET` | `/v1/facts/{id}/chain` | `?direction=&max_depth=` | `Fact[]` | Premium |
| **Propagate Taint** | `POST` | `/v1/facts/{id}/taint` | — | `TaintReport` | Premium |

### 3.3 Coordination (Pillar 3)

| Operation | Method | Path | Input | Output | Tier |
|:----------|:------:|:-----|:------|:-------|:-----|
| **Register Agent** | `POST` | `/v1/agents` | `{name, agent_type?, public_key?}` | `Agent` | Open |
| **Get Agent** | `GET` | `/v1/agents/{id}` | — | `Agent` | Open |
| **Vote** | `POST` | `/v1/facts/{id}/vote` | `{agent_id, value, reason?}` | `VoteResult` | Premium |

### 3.4 Verification (Pillar 5)

| Operation | Method | Path | Input | Output | Tier |
|:----------|:------:|:-----|:------|:-------|:-----|
| **Guard Check** | `POST` | `/v1/trust/guard` | `{content, project, fact_type?}` | `{pass: bool, warnings: TrustError[]}` | Open |
| **Compliance Report** | `GET` | `/v1/trust/compliance` | `?project=` | `AuditReport` | Premium |

### 3.5 System

| Operation | Method | Path | Input | Output | Tier |
|:----------|:------:|:-----|:------|:-------|:-----|
| **Status** | `GET` | `/v1/status` | — | `{facts, projects, db_size, uptime}` | Open |
| **Health** | `GET` | `/v1/health` | — | `{status: "ok"}` | Open |

---

## 4. Operation Count

| Tier | Operations | Notes |
|:-----|----------:|:------|
| **Open** | 14 | Store, batch, get, list, search, recall, history, deprecate, register_agent, get_agent, verify, guard_check, status, health |
| **Premium** | 4 | causal_chain, propagate_taint, vote, compliance_report |
| **Total** | 18 | |

---

## 5. SDK Mapping

Current SDK surface is documented in [`docs/sdks.md`](../sdks.md).

The mounted HTTP clients in this workspace expose these public methods today:

| Client | Methods |
|:-------|:--------|
| `CortexClient` | `store`, `search`, `recall`, `deprecate`, `status`, `create_key`, `list_keys` |
| `AsyncCortexClient` | `store`, `store_many`, `search`, `recall`, `deprecate`, `export`, `status`, `create_key`, `list_keys` |

---

## 6. MCP Tool Mapping

| MCP Tool | API Operation | Status |
|:---------|:-------------|:------:|
| `cortex_store` | `POST /v1/facts` | ✅ Exists |
| `cortex_search` | `POST /v1/facts/search` | ✅ Exists |
| `cortex_status` | `GET /v1/status` | ✅ Exists |
| `cortex_ledger_verify` | `GET /v1/ledger/verify` | ✅ Exists |
| `cortex_trace_episode` | — | ⚠️ Internal (no public REST mapping) |
| `cortex_trace_chain` | `GET /v1/facts/{id}/chain` | ✅ Exists |
| `cortex_shannon_report` | — | ⚠️ Internal (no API mapping) |
| `cortex_handoff` | — | ⚠️ Internal (session-specific) |
| `cortex_embed` | — | ⚠️ Internal (infra-specific) |
| — | `POST /v1/facts/{id}/vote` | 🆕 New |
| — | `GET /v1/trust/compliance` | 🆕 New |
| — | `POST /v1/trust/guard` | 🆕 New |
| — | `POST /v1/facts/{id}/taint` | 🆕 New |

---

## 7. Migration from Current SDK

Legacy migration notes were retired from this document because they had drifted
from the current mounted clients and routes. Use [`docs/sdks.md`](../sdks.md)
plus [`docs/api.md`](../api.md) as the living contract.

---

## 8. Phase 2 Verdict

**18 mounted operations documented across 5 domains.** 14 open-tier, 4 premium-tier.

The API surface resolves all 4 P1 gaps from Phase 1:

| P1 Gap | Resolution |
|:-------|:----------|
| No unified recall API | Separate `search` plus project-scoped `GET /v1/projects/{project}/facts` |
| No external event bus | Deferred to Phase 4 (Workstream C) — SSE endpoint on `/v1/events` |
| No rejection API | `TrustError` model with codes, categories, and remediation hints |
| Dedup predicate drift | Fixed in contract: `is_tombstoned` is the canonical predicate |

**Recommendation**: Proceed to Phase 3 (Gap Analysis & Build Plan). The contract is frozen.
