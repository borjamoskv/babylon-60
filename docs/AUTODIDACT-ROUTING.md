# Autodidact-Ω Routing Spec

## Overview

Autodidact-Ω is the cognitive routing layer of CORTEX-Persist, designed to enforce the **Second Law (Ω₂: The Thermodynamic Law)** at the prompt level. It prevents the waste of high-performance reasoning on low-complexity tasks and ensures that high-entropy problems reach the appropriate "Thinking" models.

## Metrics Architecture

The router uses two primary metrics to determine the complexity tier of a payload:

### 1. Shannon Entropy (H)
Measures the information density per character.
$$H = -\sum p_i \log_2(p_i)$$
- **High H**: Deep technical code, math, or dense non-linear text.
- **Low H**: Repetitive patterns, simple conversational greetings, boilerplate.

### 2. Kolmogorov Complexity Proxy (K)
Approximated via the Zlib compression ratio.
$$K = \frac{len(compressed)}{len(original)}$$
- **High K**: Highly irregular, non-redundant information (closer to 1.0 or > 1.0 for short strings).
- **Low K**: Highly redundant, easily compressible patterns.

## Complexity Tiers

| Tier | Range (H) | Range (K) | Action |
| :--- | :--- | :--- | :--- |
| **LOW** | < 3.8 | < 0.15 | Use standard conversational model. |
| **OPTIMAL** | 4.0 - 5.5 | 0.15 - 0.45 | Default routing path (Balanced). |
| **HIGH** | > 5.5 | > 0.60 | **Escalate to REASONING** (Intent Elevation). |
| **ANOMALOUS** | > 7.5 | < 0.05 | Flag for noise/attack (Entropy Quarantine). |

## Implementation Details

The router is implemented as a wrapper around a `BaseProvider` in `cortex/extensions/llm/autodidact_router.py`. It intercepts the `CortexPrompt` before execution, modifies the `intent` attribute if necessary, and logs the telemetry under the Ω₃ (Byzantine) validation trace.

### Configuration
Enabled via environment:
```bash
CORTEX_AUTODIDACT_ROUTING=true (Default)
```

## Telemetry & Audit
All routing decisions emit a `telemetry` event with the exact $H$ and $K$ values, allowing for offline audit of "Cognitive Waste" vs "Cognitive Yield".
