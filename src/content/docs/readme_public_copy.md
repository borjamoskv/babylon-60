---
title: "CORTEX-Persist"
description: "CORTEX Persist Documentation — CORTEX-Persist"
---


> Verifiable memory and decision records for AI agents.

**Track what an agent saw, decided, and changed - with tamper-evident history.**

Local-first. SHA-256 hash-chained. Merkle checkpoints. Audit-ready.

CORTEX Persist adds a verification layer around agent memory and decision state. It turns facts, decisions, and derived state into tamper-evident records you can review later instead of reconstructing them from logs.

## Why CORTEX

- **Verify continuity**: Hash-chained memory detects post-hoc mutation.
- **Seal batches**: Merkle checkpoints make larger verification runs practical.
- **Stay local-first**: Start with SQLite on one machine before adding more infrastructure.
- **Export evidence**: Produce audit-ready artifacts instead of reconstructing events from logs.

## Features
- **Tamper-evident ledger**: Cryptographic history for memory operations.
- **Hybrid retrieval**: Combine vector and lexical search.
- **Memory governance**: Promote, compact, decay, or archive memory intentionally.
- **Audit-ready history**: Recover what happened without narrative guesswork.

## Quickstart

```bash
pip install cortex-persist
cortex init
cortex store risk-bot "Transaction flagged: IP mismatch" --type decision --source agent:risk-bot
cortex trust-ledger verify
```

## Documentation

- [Quickstart](quickstart.md)
- [API](api.md)
- [Security Model](SECURITY_TRUST_MODEL.md)
- [Roadmap](cortex_v8_roadmap.md)
- [Contributing](CONTRIBUTING.md)

## License
Apache 2.0
