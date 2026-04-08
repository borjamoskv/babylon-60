---
title: "Anatomy of a CORTEX Audit Pack"
description: "CORTEX Persist Documentation — Anatomy of a CORTEX Audit Pack"
---

When operating autonomous AI systems in high-risk or regulated environments, stating "the agent decided to do X" is usually not enough. You need an exportable, verifiable record. CORTEX generates **Audit Packs**: JSON artifacts that capture the event, the ledger proof, and the verification path in one place.

> **View Live Artifact:** [Download `examples/audit_proof_artifact.json`](../examples/audit_proof_artifact.json)

---

## 1. The Core Payload (What happened)

Every record binds context to an explicitly defined agent, tenant, and timestamp.

```json
  "audit_receipt": {
    "tenant_id": "customer-123",
    "project": "fin-fraud-bot",
    "agent_id": "risk-bot",
    "fact_id": 42042,
    "fact_type": "decision",
    "content": "Transaction flagged: IP mismatch...",
    "timestamp": "2026-03-31T18:42:01.192Z"
  }
```

* **Why it matters:** In traditional logs, this metadata can be overwritten, deleted, or lost during retention changes. In CORTEX, the payload is tied to a verifiable ledger entry.

## 2. The Cryptographic Proof (Why it matters)

The exact payload from Step 1 is hashed, and that hash is chained to the previous state of the memory system. The result is a ledger entry that can be checked later for continuity and tamper evidence.

```json
  "cryptographic_proof": {
    "ledger_index": 142095,
    "previous_hash": "e3b0c44298...",
    "current_hash": "8f4a2b9e61...",
    "merkle_root_sealed": true,
    "proof_of_work_nonce": 98412,
    "tamper_detected": false,
    "signature": "sig_0x42f7c0a..."
  }
```

* **`previous_hash` & `current_hash`:** Help detect insertion, deletion, or reordering of historical records.
* **`merkle_root_sealed`:** Indicates the local block is connected to a wider signed snapshot.
* **`tamper_detected`:** If someone edits the row directly using raw SQL, verification should fail on a later read.

## 3. The Verification Command (How to test it)

The audit pack provides the exact CLI instruction required for an auditor, operator, or reviewer to verify the data against the live database without writing code.

```json
  "verification_command": "cortex verify <FACT_ID>"
```

* **Why it matters:** Reviewability depends on reproducibility. A stakeholder should be able to run the command and check the record directly.

## Conclusion

Standard vector stores (Pinecone, Milvus, Qdrant) give you similarity.
Standard logging platforms (Datadog, Elastic) give you timestamps.

**CORTEX Persist gives you a verifiable record of what was stored and whether it still matches the ledger.**
