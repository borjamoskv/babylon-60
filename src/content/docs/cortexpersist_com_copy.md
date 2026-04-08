---
title: "cortexpersist.com — Landing Page Copy"
description: "CORTEX Persist Documentation — cortexpersist.com — Landing Page Copy"
---


> Home copy lista para pegar en cortexpersist.com.
> El orden correcto arriba del fold es: 1. hero, 2. proof strip de 3 bloques, 3. problema, 4. solución, 5. demo, 6. features, 7. use cases, 8. technical credibility, 9. CTA final.

---

## 1. Hero

**Verifiable memory and decision records for AI agents.**

Track what an agent saw, decided, and changed with tamper-evident history.

Local-first. SHA-256 hash-chained. Merkle checkpoints. Audit-ready.

[Get Started] [View Demo]

*(Edge variant más agresiva:)*
> **Your AI can act. Add a verifiable record around it.**
> Persistent memory, tamper-evident history, and audit-ready exports for systems that cannot rely on editable logs.

---

## 2. Proof strip

**Store durable facts**
Capture decisions, errors, discoveries, and operational context as typed memory.

**Verify continuity**
Hash-chain records and seal batches so later verification is fast and defensible.

**Export evidence**
Turn agent history into review-ready artifacts instead of reconstructing events from logs.

---

## 3. Problem

**Most AI systems can generate output. Fewer can show a reliable record of how they got there.**

Agents are getting better at acting, calling tools, and producing plausible responses.
What they still lack is durable operational memory with verification.

Without that layer, systems drift, repeat work, lose context, and leave weak audit trails.

You often do not have a durable record.
You have fragments, logs, and post-hoc reconstruction.

---

## 4. Solution

**CORTEX-Persist adds the missing verification layer**

CORTEX-Persist is a local-first memory and verification layer for AI systems that need to remember, retrieve, and verify what happened.

It combines:
- structured memory
- tamper-evident ledgering
- hybrid retrieval
- memory lifecycle governance
- audit-ready history

So your stack can do more than continue text.
It can preserve a reviewable history of decisions and state changes.

---

## 5. Demo section

**From event to evidence in under a minute**

**1. Store memory**
```bash
cortex init
cortex store risk-bot \
  "Transaction flagged: IP mismatch" \
  --type decision \
  --source agent:risk-bot
```

**2. Generate lineage**
Each write can be chained into a tamper-evident ledger with transaction ID, timestamp, hash, and previous hash.

**3. Retrieve context**
```bash
cortex search "transaction ip mismatch"
```

**4. Verify integrity**
```bash
cortex trust-ledger verify
```

Result: persistent memory with searchable context and verifiable history.

[Run the Demo] [Read the Docs]

---

## 6. Feature grid

**Built for memory that needs to stay reviewable over time**

**Structured Memory**
Store facts, decisions, discoveries, and errors as typed units with metadata, confidence, and temporal validity.

**Tamper-Evident Ledger**
Attach cryptographic lineage to memory operations so decision history is not left to interpretation.

**Hybrid Retrieval**
Combine semantic and lexical retrieval for context that is actually reusable in live systems.

**Memory Governance**
Promote, compact, decay, archive, or discard memory instead of turning context into a permanent landfill.

**Local-First Runtime**
Start with SQLite and sqlite-vec locally. Extend to cloud backends when scale or deployment needs change.

**Audit-Ready History**
Support internal review, compliance workflows, and postmortems with exported evidence instead of manual reconstruction.

---

## 7. Use cases

**Where CORTEX-Persist hits hardest**

**AI agents with tools**
Keep reliable context across steps, sessions, and agent boundaries.

**Long-running automation**
Reduce repetition, drift, and memory loss in workflows that operate over time.

**Compliance and audit**
Maintain verifiable operational history for regulated or review-heavy environments.

**Decision systems**
Track not only the output, but the lineage behind how a system arrived there.

---

## 8. Why not just use a vector database?

**Because similarity is not lineage**

A vector database can retrieve related text.
It does not tell you what was stored, when it changed, how it was derived, or whether the history was tampered with.

CORTEX-Persist adds the missing layers:
- typed memory
- temporal validity
- confidence levels
- cryptographic lineage
- governed lifecycle
- auditability

Memory without integrity is still storage, but it is harder to rely on when decisions matter.

---

## 9. Technical credibility

**Built for real systems**
- Python-first architecture
- SQLite and sqlite-vec by default
- optional cloud extensions
- encryption at rest
- async-friendly design
- CLI and API surfaces
- typed package support
- memory lifecycle controls

This is infrastructure for systems that operate repeatedly, not a one-shot prompt wrapper.

---

## 10. CTA block

**Make your AI stack remember with a verifiable record**

Start with persistent memory.
Add lineage when memory starts to matter.
Keep both when review and accountability become requirements.

[Get Started] [View Demo] [GitHub]

---

## Extras

**Microcopy & Navigation**
- Nav: Product, Quickstart, Docs, GitHub, Security
- CTA variants: Get Started, Explore GitHub, Read the Docs, Verify the Ledger
- Footer one-liner: Memory for AI agents that need reviewable history.

**GitHub Integration Strings**
- **Description:** Verifiable memory and decision records for AI agents.
- **README Opening:** Verifiable memory and decision records for AI agents.

---
**Notas de implementación:** No metas termodinámica, Ω ni doctrina en el primer scroll. Eso va en una página aparte tipo *Architecture / Principles / Why CORTEX*.
