# SDKs

CORTEX provides official SDKs for Python and JavaScript/TypeScript.

---

## Python SDK

The primary supported Python interface is the local engine, distributed as `cortex-persist` on PyPI.

### Install

```bash
pip install cortex-persist
```

### Basic Usage

```python
from cortex import CortexEngine

# Synchronous usage
engine = CortexEngine(db_path="~/.cortex/cortex.db", auto_embed=True)
engine.init_db_sync()

# Store
fact_id = engine.store_sync("my-project", "Python is great", fact_type="knowledge")

# Search
results = engine.search_sync("programming languages", top_k=5)

# Recall all facts for a project
facts = engine.recall_sync("my-project")
```

### Async Usage

```python
from cortex import CortexEngine

async with CortexEngine() as engine:
    fact_id = await engine.store(
        project="my-agent",
        content="User prefers dark mode",
        fact_type="knowledge",
        tags=["ui", "preferences"],
    )

    results = await engine.search("user interface preferences")
    facts = await engine.recall("my-agent")
```

### Multi-Tenant Usage

```python
engine = CortexEngine()

# Store with tenant isolation
await engine.store(
    content="Approved loan #443",
    fact_type="decision",
    project="fintech-agent",
    tenant_id="enterprise-customer-a",
)
```

### REST API Clients

For remote HTTP access, use the REST clients that ship inside the package:

```python
from cortex.api.client import CortexClient
from cortex.api.async_client import AsyncCortexClient

client = CortexClient(base_url="http://localhost:8484", api_key="ctx_your_api_key")
fact_id = client.store("demo", "Hello from the REST client")

async with AsyncCortexClient(base_url="http://localhost:8484") as async_client:
    results = await async_client.search("hello", k=3)
```

### Consensus

```python
agent_id = await engine.consensus.register_agent("agent:claude")
score = await engine.consensus.vote_v2(
    fact_id=42,
    agent_id=agent_id,
    value=1,  # 1 = verify, -1 = dispute
)
```

### Common Engine Methods

The engine exposes a mixed surface: core persistence has sync wrappers, while broader lifecycle and analysis APIs are async-first.

| Sync Wrapper | Async Method | Description |
|:---|:---|:---|
| `init_db_sync()` | `init_db()` | Initialize database schema |
| `store_sync()` | `store()` | Store a fact |
| `search_sync()` | `search()` | Semantic search |
| `recall_sync()` | `recall()` | Recall facts for a project |
| `close_sync()` | `close()` | Close connections and resources |

Async-only methods used commonly in applications include `store_many()`, `history()`, `retrieve()`, `get_fact()`, `stats()`, `deprecate()`, `update()`, and `vote()`.

---

## JavaScript / TypeScript SDK

> **Status:** Early development. Available at `sdks/js/`.

### Install (from source)

```bash
cd sdks/js
npm install
```

### Usage

```typescript
import { CortexClient } from '@cortex-persist/sdk';

const cortex = new CortexClient({
  baseUrl: 'http://localhost:8484',
  apiKey: 'ctx_your_api_key',
});

// Store a fact
const result = await cortex.store({
  project: 'my-app',
  content: 'User prefers dark mode',
  factType: 'knowledge',
});

// Search
const facts = await cortex.search({
  query: 'user preferences',
  topK: 5,
});

// Recall
const allFacts = await cortex.recall('my-app');
```

### Planned: npm Package

```bash
# Coming Q2 2026
npm install @cortex-persist/sdk
```

---

## REST API

Both SDKs communicate with the CORTEX REST API. You can also use the API directly with any HTTP client:

```bash
# cURL
curl -X POST http://localhost:8484/v1/facts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ctx_your_key" \
  -d '{"project": "demo", "content": "Hello from cURL", "fact_type": "knowledge"}'
```

See the [REST API Reference](api.md) for all endpoints.

See `examples/curl_cheatsheet.md` for more cURL examples and `examples/postman_collection.json` for Postman.
