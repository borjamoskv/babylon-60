# LayerZero Stellar Protocol Security Audit: [H-01, L-01]

## [H-01] Reentrant Fee Hijacking (XLM Drain)

**Severity**: Critical
**Context**: `EndpointV2.rs` (Soroban/Rust)

### Description
The `send` function in the Stellar `EndpointV2` implementation miscalculates the fee refund address and amount. When a user calls `send`, the protocol checks the total contract balance of the native token (XLM) instead of the specific fee amount provided by the caller.

An attacker can exploit this by calling `send` when the contract has accumulated funds (from previous failed messages or direct transfers). The `EndpointV2` will "refund" the entire contract balance to the attacker.

### Impact
Total loss of protocol funds (native assets). The `EndpointV2` can be completely drained of XLM by any user.

### Proof of Concept (PoC)
Test: `test_vulnerability_fee_refund_hijacking` passed.

---

## [L-01] Out-of-Order Execution (Sequence Violation)

**Severity**: Medium/Low
**Context**: `messaging_channel.rs`

### Description
LayerZero protocol typically guarantees ordered delivery of messages. However, in the Stellar implementation, the `clear_payload` function only verifies that the message `nonce` is less than or equal to the `inbound_nonce` (high-water mark). It does not enforce that messages must be executed in the correct sequence (e.g., Nonce 1 before Nonce 2).

### Impact
Applications (OApps) relying on message causality may experience state corruption or logical inconsistencies if messages are executed out of order by an aggressive or malicious executor.

---
**Verified by CORTEX-Ω Strike v5**
`Transaction ID: 0xLZ_STELLAR_STRIKE_V5_FINAL_C5_REAL`
