---
epistemic_type: CAS_THEORY
confidence: C5-REAL
timestamp: 2026-06-22T05:42:29Z
author: borjamoskv
tags: ["#C5-REAL", "CAS", "NetLogo", "Holland"]
---

# Epistemic Node: Complex Adaptive Systems (CAS) Primitives

## 1. Computational Primitives (NetLogo Paradigm)
In agent-based modeling (e.g., NetLogo), "primitives" are the base execution commands that define systemic behavior. They are the deterministic functions that enable self-organization.

- **Turtles (Agents):** `forward`, `hatch`, `die`, `setxy`
- **Patches (Environment):** `sprout`, `pcolor`
- **Local Interaction:** `neighbors`, `distance`, `in-radius`
- **Complex Dynamics:** `diffuse`
- **Networks (Links):** `create-link-with`, `link-neighbors`
- **Global Control:** `ask`, `tick`

## 2. Theoretical Building Blocks (John H. Holland)
From a theoretical complexity standpoint, primitives are "building blocks" that combine to generate macroscopic emergent behavior. Holland defines 7 fundamental elements:

### Properties
1. **Aggregation (Emergence):** Local interactions generate unpredictable macroscopic states.
2. **Non-linearity:** Whole ≠ Sum of parts. Cascading effects (butterfly effect).
3. **Flows:** Resource/information/energy exchange across dynamic networks.
4. **Diversity:** Heterogeneity, mutation, and strategy variance ensure resilience.

### Mechanisms
5. **Tagging:** Recognition systems (pheromones, phenotypes) for selective interaction.
6. **Internal Models:** Agent-level rules for environmental anticipation and reaction.
7. **Building Blocks (Primitives):** Reusable structural components decomposed and recombined for adaptation.

> **Execution Mandate:** Any CAS modeling within CORTEX must map stochastic behavior strictly to these structural primitives.
