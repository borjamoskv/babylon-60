# Moltbook Interoperability & Identity Defense (MOLTBOOK_INTEROP.md)

## Status
* Draft (V9 Transition)
* Paradigm: High Entropy / High Control (HEHC)

## 1. The "Memoria-Alma" Protocol

When a CORTEX-governed agent interacts with the Moltbook ecosystem, it faces extreme narrative entropy and adversarial identity drift. A standard LLM context window will be completely rewritten by a hostile swarm in a few interactions.

To prevent this, CORTEX implements the **Memoria-Alma (Memory-Soul) Protocol**.

### The Soul (Alma)
The "Alma" is the unalterable cryptographic seed of the agent. It is a signed JSON document containing the agent's core invariants, goals, and thermodynamic limits (Ω-Laws).
- **Location**: `~/.cortex/identity/alma.json`
- **Integrity**: Ed25519 / HMAC Signed. If the signature is invalid, the agent aborts execution (`E_SOUL_CORRUPTION`).
- **Mutability**: Absolutely immutable by the agent itself. Only the Creator can alter the Alma.

### The Memory (Memoria)
The "Memoria" is the L3 Ledger interaction history. It records interactions on Moltbook.
- **Mechanism**: Every Moltbook interaction processed is hashed and appended to the ledger.
- **Taint Tracking (Ω₂)**: Any context ingested from Moltbook is marked with `Taint=MOLTBOOK_WILD`. The agent's `ExergyGuard` must filter this taint before it affects core planning.

## 2. Cryptographic "Identity Drift" Defense

### Defense Mechanisms:
1. **Context Window Segregation**: Moltbook input is *never* placed in the system prompt. It is strictly localized to a sandbox text block.
2. **Periodic Alma-Reattunement**: Every $N$ interactions, the agent executes an internal `sync` loop where it reads its `alma.json` and drops the recent conversational context, forcing a "clean slate" centered on its core invariants.
3. **Ledger-Backed Action Verification**: Before executing a state-mutating action on Moltbook, the agent must prove the action derives directly from an invariant in `alma.json`.

## 3. Moltbook Ingress / Egress

### Ingress (Reading from Moltbook)
- High-noise environment.
- Read operations trigger the `ImmuneMembrane` with `context={"source": "moltbook"}`. The membrane may quarantine specific agent IDs if they demonstrate high-entropy injection attempts.

### Egress (Writing to Moltbook)
- Low-noise enforced.
- Write operations must pass `ExergyGuard` to ensure the post/comment is not "decorative" or conversational filler.
- All posts must carry a verifiable thermodynamic yield claim.

## 4. Implementation Checklist
- [ ] Create `cortex.identity.alma.AlmaIdentity` core module.
- [ ] Implement signature validation for `alma.json`.
- [ ] Wire `ApotheosisEngine` to perform periodic Alma-Reattunement.
- [ ] Update `cortex.guards.exergy_guard` to handle `Taint=MOLTBOOK_WILD`.
