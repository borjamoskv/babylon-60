# CORTEX V7 Memory Architecture — The 4-Cycle Singularity 

> **Status:** IMPLEMENTED (April 2026)  
> **Engine:** `cortex/memory/*`  
> **Epistemic Posture:** Zero-Hallucination, O(1) Local-First, Thermodynamically Optimized.

---

> [!IMPORTANT]
> **The Context Rot Problem is Solved.** 
> The traditional multi-agent memory wall—where long contexts collapse into noise and stochastic hallucinations—has been bypassed. Native CORTEX v7.0 introduces a deterministic 4-tier Sovereign Memory Substrate. It runs completely offline on the edge, anchored by SQLite (and `sqlite-vec`/Mmap), effectively eliminating external vectors/graph costs and API latency.

## 1. Ontological Graph RAG (Ciclo 1)
**Location:** `cortex/memory/graph_store.py`

Stochastic generation is an inherently unstable mechanism for causal reasoning. By implementing a Property Graph entirely over SQLite:
* **Deterministic Multi-hop:** Swarm agents traverse exact, cryptographically verifiable edges. If `A -> [CAUSED] -> B -> [RESOLVED] -> C` exists in the graph, the answer is exact. If it does not exist, the inference aborts.
* **Hybrid Defense:** Combined with `aiosqlite` and `sqlite-vec` (Vector Store), agents quickly retrieve approximate contexts but *verify* the underlying logic through graph topology.

## 2. Procedural RLVR — Algorithmic Muscle Memory (Ciclo 2)
**Location:** `cortex/memory/procedural.py` & `cortex/memory/rlvr_evaluator.py`

Reinforcement Learning from Verifiable Rewards (RLVR) provides the thermodynamic anchor for autonomous action. 
* **The Striatal Value Engine:** Actions are weighted by a continuous `q_value` metric `[-1.0, 1.0]`. 
* **Thermodynamic Penalty:** The system autonomously records execution success and latency. A fast, correct operation receives dopamine (increases the likelihood of the tool/skill being selected). Slower or unstable tasks decay exponentially via a half-life algorithm.

## 3. Autobiographical Scratchpad — MemGPT Paradigm (Ciclo 3)
**Location:** `cortex/memory/working.py`

Stateless execution destroys agent identity. Borrowing from Letta/MemGPT architectures:
* **Mutable Prompt Injection:** L1 Working Memory now hosts an embedded `<SCRATCHPAD>`.
* **State Operations:** Agents autonomously execute `core_memory_append` and `core_memory_replace` to constantly mutate their short-term operational theories, keeping reflection alive across standard L1 memory purges.

## 4. KV-Cache Context Prefill Engine (Ciclo 4)
**Location:** `cortex/engine/context_cache.py`

* **Asymmetric Efficiency:** Implements `get_provider_caching_kwargs` to dynamically adapt the underlying provider API (Anthropic `ephemeral`, Gemini `dynamic_cache`, vLLM `use_prefix_cache`). 
* **Zero-Exergy:** Swarm agents reload the immutable system prompt and historic blocks without recompiling tokens. The integration of 10,000 agents requires O(1) context initiation to bypass severe API rate limits and infrastructure costs.
 
---

> [!TIP]
> **Operational Paradigm**  
> To interact with the new engine, external components only route requests to `CortexMemoryManager` which now natively orchestrates Vector (`SovereignVectorStoreL2`), Ledger, Graph (`GraphStore`), and L1 (`WorkingMemoryL1`). All external cognitive boundaries have effectively been unified.
