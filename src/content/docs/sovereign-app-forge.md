---
title: "Sovereign App Forge"
description: "CORTEX translation of ephemeral collaborative app generation"
status: draft
version: 0.1
last_updated: 2026-04-07
---

# Sovereign App Forge

`@Q` showed a useful pattern: generate a single-purpose collaborative app inside an isolated browser runtime and bind it to a small host API surface. The CORTEX translation keeps the pattern and replaces the SaaS substrate.

## Primitive Mapping

| `@Q` primitive | CORTEX primitive | Reason |
| :--- | :--- | :--- |
| `useSyncedState` | `useSovereignState` | Shared state is serialized into tenant-scoped CORTEX memory, versioned, and stamped with `CORTEX-TAINT`. |
| `useLoggedInUser` | `useAgentContext` | Identity comes from the local agent/runtime profile, not an external auth SDK. |
| `generateContentStream` | `generateVectorStream` | Inference is routed through local or sovereign model backends instead of remote SaaS APIs. |

## Runtime Contract

The first CORTEX cut is intentionally narrow:

- render target: isolated `iframe`
- host bridge: `postMessage`
- bundler: `esbuild-wasm`
- state backplane: `VSA-SDM`
- network policy: local-only
- persistence model: versioned `app:state` facts through the existing write path

This keeps App Forge in `CORTEX Deepforge`. It does not bypass `Hypercore`. Generated apps may synthesize UI, but durable shared state still crosses the ordinary fact boundary with taint and tenant scope.

## State Envelope

`useSovereignState` writes a JSON envelope with:

- `app_id`
- `state_key`
- `scope`
- `version`
- `value`
- `state_hash`
- `created_at`

The host stores the envelope content as the fact payload and records `taint`, `agent_id`, `session_id`, and indexing metadata in fact `meta`. Reads reject envelopes whose taint or state hash no longer verify.

## Why This Matters

This gives CORTEX a path to ephemeral collaborative software without inheriting the trust model of Firebase-like backplanes:

- collaboration is local-first and tenant-aware
- generated UI remains disposable
- shared state remains auditable
- the trust boundary stays where CORTEX already knows how to verify it

## Next Steps

1. Add a local host runtime that injects the `$` module into an iframe sandbox.
2. Connect `SovereignAppForge.system_prompt()` to `ComposerEngine` or `Sortu`.
3. Add visual/runtime verification for generated apps before activation.
