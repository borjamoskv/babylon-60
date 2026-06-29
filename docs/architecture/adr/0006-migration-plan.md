# ADR 0006: Namespace Migration Plan (Babylon-60)

## Status
Proposed

## Date
2026-06-29

## Context
Following the approval of ADR 0005, which decouples the MOSKV corporate identity from the BABYLON-60 product and internal namespaces, a concrete, phased migration plan is required to transition the existing `cortex` Python package to the `babylon60` namespace without breaking existing integrations, test suites, or persistence layers. The codebase has over 4,700 Python imports, 400+ DB references, and 200+ environment variables tied to the old namespace.

## Decision
We will execute a structured, multi-wave migration governed by strict validation criteria and rollback capabilities.

### Wave 1: The Compatibility Layer (Alias & Façade)
**Objective**: Establish `babylon60` alongside `cortex` without migrating underlying logic.
* **Actions**:
  * Create the `babylon60` package structure.
  * In `babylon60/__init__.py`, establish a compatibility alias that proxies or re-exports symbols from `cortex`.
  * Update documentation to reference `babylon60` as the primary API, while implementation remains in `cortex`.
* **Validation Criteria**:
  * `import babylon60` succeeds seamlessly.
  * `pytest` continues to pass 100%.
  * Zero modifications to existing `cortex` core logic.

### Wave 2: Internal Module Refactoring (Bottom-Up)
**Objective**: Migrate core business logic from `cortex` to `babylon60`.
* **Actions**:
  * Incrementally move internal modules (`memory`, `ledger`, `engine`, `crypto`, etc.) from `cortex/` to `babylon60/`.
  * In `cortex/`, leave behind façade modules that import from `babylon60` and emit a `DeprecationWarning`.
  * Update all internal imports across the codebase to use `babylon60`.
* **Validation Criteria**:
  * Test suite passes with 0 failures.
  * Linters (Ruff, Pyright) report no unresolved imports.
  * External scripts (e.g., `scripts/legion_strike.py`) continue to function using the `cortex` shim.

### Wave 3: Persistence and Infrastructure Neutralization
**Objective**: Decouple DB paths, env vars, and TAINT signatures from the branding.
* **Actions**:
  * Introduce neutral Environment Variables (e.g., `MOSKV_DB_PATH`) with active fallbacks to `CORTEX_*` to guarantee backward compatibility.
  * Implement safe database migration paths to transition filenames from `cortex.db` to neutral equivalents (e.g., `runtime.db`).
  * **Critical Ledger Constraint**: Retain `CORTEX-TAINT` signature validation indefinitely for legacy entries to guarantee cryptographic unbroken chains. Begin signing new entries with a neutral or updated prefix.
* **Validation Criteria**:
  * Master Ledger continuity remains strictly verifiable.
  * No loss or corruption of existing memory facts.

### Wave 4: Ecosystem Tools & Rust FFI
**Objective**: Migrate non-Python assets, Rust FFI, and CLI interfaces.
* **Actions**:
  * Update CLI entrypoints from `cortex` to `babylon60` (retaining `cortex` as an alias).
  * Update Rust crates in `c5_workspace/` to rename packages from `cortex_*` to `babylon60_*` or neutral identifiers.
  * Update Dockerfiles, CI/CD pipelines, and configuration files (`pyproject.toml`, `Cargo.toml`).
* **Validation Criteria**:
  * Rust binaries compile successfully.
  * End-to-end tests and deployment workflows execute without errors.

### Wave 5: Deprecation and Final Purge
**Objective**: Fully deprecate and remove the `cortex` legacy namespace.
* **Actions**:
  * Completely delete the `cortex/` directory.
  * Remove `CORTEX_*` fallback logic in configuration loading.
  * Remove legacy CLI aliases.
* **Timeline**: To be executed only at the next major version boundary (e.g., v2.0.0), providing dependent systems and operators ample time for migration.

## Consequences

* **Positive**: The transition is governed, predictable, and reversible at any stage. Risk of catastrophic runtime failure is mitigated by maintaining dual namespaces.
* **Negative**: Requires temporary maintenance of façade modules, duplication of entry points, and careful handling of deprecation warnings during the transition period.
