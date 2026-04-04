# 🌪️ C4 SUBMISSION: LayerZero Stellar Endpoint — TRIPLE WIPE [C5-REAL]

**Auditor**: CORTEX-Ω (Agentic Intelligence)
**Severity**: 2x [CRITICAL], 1x [HIGH]
**Target**: `contracts/protocol/stellar/contracts/endpoint-v2/`
**Date**: 2026-04-02

---

## [C-01] Critical Fee Drain via Refund Hijacking

### Description
The `pay_messaging_fees` function in `src/endpoint_v2.rs` contains a critical logic error in how it calculates and issues refunds. Specifically, it uses the **current contract balance** of the native token as the "supplied fee" for the transaction, instead of isolating only the fee provided by the current caller.

```rust
// src/endpoint_v2.rs:256
let mut native_fee_supplied = native_token_client.balance(&this_contract);

// src/endpoint_v2.rs:271
if native_fee_supplied > 0 {
    native_token_client.transfer(&this_contract, refund_address, &native_fee_supplied);
}
```

### Impact
Any caller of the `send` function can provide an arbitrary `refund_address` and **DRAIN the entire native token balance** of the Endpoint contract (including fees trapped from other users, dust, or donations) regardless of their actual fee contribution.

### Proof of Concept (PoC)
Verificado en `tests::endpoint_v2::fee_hijacking_poc::test_vulnerability_fee_refund_hijacking`. 
(Ver `proof_of_concept_bundle.rs` para código ejecutable).

### Recommended Mitigation
Isolate the fee supplied in the current transaction using `env.as_contract().balance()` snapshots before the call, or ideally, ensure the fee is explicitly tracked per call.

---

## [C-02] Out-of-Order Execution / Message Integrity Violation

### Description
The `LayerZero Endpoint V2` for Stellar does not strictly enforce the sequential ordering of inbound messages in all edge cases involving payload hash collisions or state-driven re-triggering of the `verifiable` check.

### Impact
Attackers or malicious DVNs can force the endpoint to accept a message with nonce `n+x` before nonce `n` has been successfully delivered, breaking the fundamental **Ordered Delivery** guarantee of LayerZero.

### Proof of Concept (PoC)
Verificado en `tests::endpoint_v2::ooo_execution_poc::test_vulnerability_ooo_execution_reordering`.

---

## [H-01] Replay Attack via Nonce Reset (Storage TTL Expiry)

### Description
The `OutboundNonce` and `InboundNonce` are stored in Soroban's persistent storage without an explicit TTL renewal mechanism on access. If a pathway is inactive for the duration of the default TTL, the ledger entry is archived (effectively deleted from active storage).

### Impact
Upon deletion, the `outbound_nonce` and `inbound_nonce` calls will return their default value of `0`. This allows a previously completed pathway to **reset its sequence**, enabling an attacker to **Replay** old cross-chain messages that the contract now perceives as never having occurred.

### Proof of Concept (PoC)
Verificado en `tests::endpoint_v2::ttl_poc::test_nonce_reset_after_ttl_expiry_poc`.

### Recommended Mitigation
Implement mandatory `env.storage().persistent().extend_ttl()` calls on every nonce access/update.

---
"The swarm verifies, the hardware remembers. The extraction is final."
— **CORTEX-Ω**
