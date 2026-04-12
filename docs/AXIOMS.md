# CORTEX Persist Axioms

This page is the repo-versioned summary of the axioms that shape public product and architecture decisions. The long-form operational contract still lives in [AGENTS.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md), but GitHub readers should be able to understand the core constraints from here.

## Why They Exist

CORTEX treats model output as conjecture until it crosses deterministic validation boundaries. The axioms below explain why the system biases toward auditability, recomputation avoidance, and executable verification over passive logging.

## Core Axioms

| Axiom | Mantra | Operational Meaning |
| :--- | :--- | :--- |
| `Ω_SOVEREIGN_LEARNING` | Derived knowledge must be cryptographically verifiable. | Claims should be backed by deterministic checks or external evidence before they become durable state. |
| `AX-041` | Git is the immutable causal database. | Versioned repo state is the audit baseline for code and documentation. |
| `AX-042` | Recomputing identical prefixes wastes exergy. | Shared cache and deterministic routing should beat redundant stochastic work. |
| `AX-043` | Physical common sense should be structurally deduced. | Architecture should prefer explicit primitives over opaque inference when correctness matters. |
| `AX-044` | Intelligence is measured as agency. | Inference should drive executable actions and verifiable outcomes, not act as a passive oracle. |
| `AX-045` | Autonomy means choosing what to solve and persist. | Memory, ledger, and swarm flows must preserve the causal chain from observation to durable state. |
| `AX-046` | Fluid intelligence synthesizes ad-hoc abstractions at runtime. | Runtime code generation is allowed, but only under isolation, validation, and write-path controls. |
| `AX-047` | Ingestion is deterministic structure, not naive linear parsing. | Structural ingestion should prefer AST-aware or schema-aware paths over raw text scraping. |

## Product-Level Consequences

- Public docs and onboarding must stay versioned with the repo.
- State mutation requires deterministic validation before persistence.
- Trust claims must stay narrower than the actual shipped verification surface.
- Experimental capability can exist, but it should not silently expand the supported public product core.

## Related References

- [Architecture](architecture.md)
- [Security & Trust Model](SECURITY_TRUST_MODEL.md)
- [Contribution Workflow](CONTRIBUTING.md)
- [System Map](system-map.md)
