---
title: "CORTEX"
description: "CORTEX Persist Documentation — CORTEX"
---


> **Verifiable memory and decision records for AI agents.**
> Track what an agent saw, decided, and changed with tamper-evident history.
> *Local-first. SHA-256 hash-chained. Merkle checkpoints. Audit-ready.*

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)
![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)

---

## Why CORTEX?

AI systems can generate output, call tools, and mutate state. What they usually cannot do is show what memory existed at decision time or whether that memory changed later.

CORTEX does not replace your memory stack. It adds a verifiable record on top of it.

### Why not just logs or a vector DB?

Traditional logging and standard vector stores help with retrieval and observability. They do not give you a verifiable record of agent context and decisions. CORTEX adds that missing layer.

| Feature                    | Standard Logs (Datadog/ELK) | Standard Vector DB (Pinecone/Qdrant) | **CORTEX Persist**                        |
|:---------------------------|:----------------------------|:-------------------------------------|:------------------------------------------|
| **Primary Goal**           | Observability & Debugging   | Semantic Search & RAG                | **Verifiable memory and decision records** |
| **Write Integrity**        | Overwritable / Editable     | Silent CRUD operations               | **Append-Only + Cryptographic Hash**      |
| **Fact Mutability**        | Easy (API/Admin access)     | Easy (API/Admin access)              | **Tamper-evident, append-oriented records** |
| **Evidence Export**        | Text dumps                  | JSON extracts                        | **Portable audit packs**                  |

> **See a real artifact**: [View exported audit pack](../examples/audit_proof_artifact.json)

---

## Core Capabilities

| Capability | What It Does |
|:---|:---|
| 🔗 **Immutable Ledger** | Every fact is SHA-256 hash-chained. Tamper becomes detectable. |
| 🌳 **Merkle Checkpoints** | Batch verification for larger memory sets. |
| 🔐 **Privacy Shield** | Ingress controls for sensitive payloads. |
| 🧠 **Structured Memory** | Facts, decisions, and derived state with lineage. |
| 📊 **Audit Exports** | Evidence packs for review, incidents, and compliance work. |
| 🔍 **Hybrid Search** | Semantic and lexical retrieval in one stack. |
| 🏠 **Local-First** | SQLite by default. No cloud required to start. |
| ☁️ **Cloud Extensions** | Pluggable infrastructure when deployment needs grow. |

---

## Core Trust Capabilities

The platform also exposes five canonical capabilities. These names map to the architecture, but the behavior is concrete:

1. **Deterministic admission checks** for generated claims before persistence.
2. **Hash continuity and checkpoint verification** for ledger integrity.
3. **Explicit handling of uncertain or tainted memory** instead of silent blending.
4. **Rollback-aware write flows** across the mutation path.
5. **Isolated self-modification paths** for runtime code generation.

[Read the canonical definition](CORTEX-NATIVE-TECHNOLOGIES.md)

---

## Subsystem Map

CORTEX organizes the existing codebase into five named subsystems. The names are documentation labels only; package paths stay unchanged.

- `CORTEX Hypercore` for trust, validation, and persistence
- `CORTEX Overmind` for orchestration and agent control
- `CORTEX Deepforge` for synthesis and reasoning
- `CORTEX Primeflow` for runtime execution and delivery
- `CORTEX Coreshift` for memory evolution and schema transitions

[Read the full system map](system-map.md)

---

## Quick Start

```bash
pip install cortex-persist
cortex init
cortex store risk-bot "Transaction flagged: IP mismatch" --type decision --source agent:risk-bot
cortex trust-ledger verify
```

[View Audit Evidence →](../examples/audit_proof_artifact.json){ .md-button .md-button--primary }
[Architecture →](architecture.md){ .md-button }
[View on GitHub →](https://github.com/borjamoskv/Cortex-Persist){ .md-button }

---

## Who Is CORTEX For?

- **AI engineers** building agents that need durable, auditable memory.
- **Security and compliance teams** that need evidence instead of narrative reconstruction.
- **Platform teams** that want to add verification without replacing their stack.
- **Builders shipping locally first** who still want a credible trust story.

---

## Documentation

| Section | Description |
|:---|:---|
| [Quickstart](quickstart.md) | Get running in 5 minutes |
| [Installation](installation.md) | All install methods and extras |
| [Architecture](architecture.md) | Deep dive into the system design |
| [System Map](system-map.md) | Canonical `CORTEX Hypercore` / `CORTEX Overmind` / `CORTEX Deepforge` / `CORTEX Primeflow` / `CORTEX Coreshift` mapping |
| [CORTEX Native Technologies](CORTEX-NATIVE-TECHNOLOGIES.md) | Canonical definition of the platform's five core trust capabilities |
| [Sovereign App Forge](sovereign-app-forge.md) | Local-first translation of the `@Q` ephemeral app pattern into CORTEX primitives |
| [CORTEX System Brief](cortex-system-brief.md) | Product, architecture, positioning, adoption path, and messaging in one place |
| [CORTEX Feature Story](cortex-feature-story.md) | Longform editorial narrative that merges the system brief and the LinkedIn story |
| [LinkedIn Article Draft](linkedin-cortex-article.md) | Publishable founder-style article based on the new subsystem taxonomy |
| [CORTEX Capabilities](CORTEX-CAPABILITIES.md) | Structural properties and governance topology |
| [SDK Surface](SDK-SURFACE.md) | Public SDK contract and stability guarantees |
| [Trust Semantics](TRUST-SEMANTICS.md) | Meaning of trust signals and degraded states |
| [Estado público, claims y límites](estado-publico-claims-y-limites.md) | Qué puede afirmarse hoy con evidencia pública y qué requiere matiz |
| [Event Model](EVENT-MODEL.md) | Canonical event envelope and delivery semantics |
| [Error Code Registry](ERROR-CODE-REGISTRY.md) | Stable rejection and failure codes |
| [CLI Reference](cli.md) | Core commands documented |
| [REST API Reference](api.md) | Versioned REST endpoints |
| [MCP Server](mcp.md) | Model Context Protocol integration |
| [Python API Reference](reference.md) | Auto-generated from source |
| [SDKs](sdks.md) | Python and JavaScript SDKs |
| [Developer Guide](developer-guide.md) | Contributing and extending CORTEX |
| [EU AI Act Compliance](compliance.md) | Article 12 mapping |
| [Security](security.md) | Threat model and security features |
| [Deployment](deployment.md) | Package install and included Docker deployment path |
| [Configuration](configuration.md) | Environment variables reference |
| [FAQ](faq.md) | Common questions, answered honestly |
| [Changelog](changelog.md) | Version history and release notes |
| [Archive](archive/index.md) | Historical snapshots, superseded proposals, and prior-state docs |

---

*by [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
