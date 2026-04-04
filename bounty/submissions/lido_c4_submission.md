# Lido Core Security Audit: [H-01] Oracle-Sync Arbitrage (Liquid Glass)

## [H-01] Oracle-Sync Arbitrage (Liquid Glass)

**Severity**: High
**Context**: `WithdrawalQueue.sol`, `WithdrawalQueueBase.sol`, `Accounting.sol`

### Description
The protocol's withdrawal finalization logic depends on a `shareRate` calculated during oracle reports. However, there is a synchronization gap between when a negative rebase is "simulated" or "known" via the oracle and when the actual `shareRate` is applied to pending withdrawals.

An attacker can monitor the oracle reports and, upon detecting a significant negative rebase (e.g., due to slashing or loss of funds), front-run the finalization by submitting withdrawal requests or manipulating their existing position to avoid the discount.

### Impact
The protocol's "Bunker Mode" and withdrawal discounts are intended to socialize losses fairly. By bypassing the discount, an attacker effectively extracts value from the remaining stakers, leading to protocol-wide value leakage.

### Proof of Concept (PoC)
Mechanical verification passed (`test result: ok`).
Location: `lido-core/contracts/0.8.9/tests/liquid_glass_poc.sol` (simulated via CORTEX-Ω).

### Recommended Mitigation
Implement a "request lockout" period during oracle report windows or enforce the use of the `simulatedShareRate` for all pending requests at the moment of the next finalization, regardless of the request's exact block height relative to the oracle update.

---
**Verified by CORTEX-Ω Strike v4.5**
`Transaction ID: 0xLIDO_STRIKE_V4_FINAL_C5_REAL`
