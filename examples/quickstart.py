"""CORTEX Quickstart — Store, Search, Ask in 10 lines.

Usage:
    pip install cortex-persist
    export CORTEX_API_KEY=your_key
    python quickstart.py
"""

from cortex.api.client import CortexClient

client = CortexClient(base_url="http://localhost:8484")

# 1. Store a fact
fact_id = client.store(
    "demo",
    "CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.",
    fact_type="knowledge",
)
print(f"Fact stored: #{fact_id}")

# 2. Search by semantic similarity
results = client.search("What is CORTEX?", k=3)
for r in results:
    print(f"  [#{r.id}] (score: {r.score:.3f}) {r.content[:80]}")

# 3. Ask with RAG (requires CORTEX_ENABLE_EXPERIMENTAL_API=1 and an LLM provider)
try:
    import httpx

    resp = httpx.post(
        "http://localhost:8484/v1/ask",
        json={"query": "What is CORTEX?", "k": 5},
        headers={"Authorization": "Bearer your_key"},
    )
    print(f"\nAnswer: {resp.json()['answer']}")
except Exception as e:
    print(f"\nRAG requires experimental API and LLM provider: {e}")

print("\nCORTEX is operational!")
