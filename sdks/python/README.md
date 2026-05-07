# CORTEX Python SDK

Thin, zero-dependency client for the [CORTEX Persist API](https://github.com/borjamoskv/Cortex-Persist).

## Install

```bash
pip install cortex-persist
```

## Usage

The working in-repo HTTP client is `cortex.api.client.CortexClient`.

```python
from cortex.api.client import CortexClient

ctx = CortexClient("http://localhost:8484", api_key="ctx_your_key")

try:
    fact_id = ctx.store(
        "myproject",
        "user prefers dark mode",
        fact_type="knowledge",
        tags=["preferences"],
    )

    results = ctx.search("what does the user prefer?", k=3, project="myproject")
    for r in results:
        print(f"[{r.score:.2f}] {r.content}")

    facts = ctx.recall("myproject")
finally:
    ctx.close()
```

## API Reference

| Method | Description |
|---|---|
| `store(project, content, fact_type, tags, metadata)` | Store a fact → returns `fact_id` |
| `search(query, k, project)` | Semantic search → `list[Fact]` |
| `recall(project, include_deprecated)` | Recall all facts → `list[Fact]` |
| `deprecate(fact_id)` | Soft-delete a fact |
| `status()` | Engine status |
| `create_key(name, tenant_id)` | Create an API key |
| `list_keys()` | List API keys |

## License

Apache-2.0
