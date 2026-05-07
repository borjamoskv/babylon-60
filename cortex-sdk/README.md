# cortex-persist

> **Give your AI agent a brain that remembers.**

Persistent memory infrastructure for AI agents. Store, search, and verify memories with semantic search and cryptographic integrity.

## Install

```bash
pip install cortex-persist
```

## Quickstart

```python
from cortex_persist import CortexClient

client = CortexClient(base_url="http://localhost:8484", api_key="ctx_your_key_here")

health = client.runtime.health()
print(health.status)
```

The domain client in this package is a draft SDK surface. The current default
REST API does not yet mount every `/v1/memory/*`, `/v1/trace/*`, or
`/v1/coordination/*` route used by the draft domains. For the stable HTTP
surface today, use `cortex.api.client.CortexClient` from the main package.

## Async Usage

```python
from cortex_persist import AsyncCortexClient

async with AsyncCortexClient(base_url="http://localhost:8484", api_key="ctx_...") as client:
    health = await client.runtime.health()
    print(health.status)
```

## Features

- **Semantic Search** — Find memories by meaning, not just keywords
- **Cryptographic Integrity** — Every memory is hash-chain verified
- **Tenant Isolation** — Your data is completely isolated
- **Temporal Queries** — Search "as of" a specific point in time
- **Batch Operations** — Store up to 100 memories in one call
- **Usage Tracking** — Monitor your API consumption

## API Reference

### `CortexClient(api_key, base_url)`

| Method | Description |
|---|---|
| `client.memory.query(input_data)` | Draft trust-aware memory query |
| `client.memory.store(project, content, ...)` | Draft memory write |
| `client.trace.get_causal_chain(fact_id)` | Draft trace lookup |
| `client.verify.verify_integrity(fact_id)` | Draft integrity check |
| `client.coordination.register_agent(...)` | Draft coordination registration |
| `client.runtime.health()` | Runtime health check |

## Plans

| Plan | Calls/month | Projects | Storage |
|---|---|---|---|
| **Free** | 1,000 | 1 | 10 MB |
| **Pro** ($29/mo) | 50,000 | 10 | 1 GB |
| **Team** ($99/mo) | 500,000 | Unlimited | Unlimited |

## Links

- **Documentation**: [GitHub Docs](https://github.com/borjamoskv/Cortex-Persist/tree/main/docs)
- **Website**: [cortexpersist.com](https://cortexpersist.com)
- **Repository**: [github.com/borjamoskv/Cortex-Persist](https://github.com/borjamoskv/Cortex-Persist)

---

*Built by [MOSKV](https://moskv.com) · Apache-2.0*
