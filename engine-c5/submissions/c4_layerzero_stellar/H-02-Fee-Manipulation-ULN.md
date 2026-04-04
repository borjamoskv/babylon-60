# [H-02] Fee Manipulation via Unvalidated Executor Quotes in `ULN302`

## Summary
The `ULN302` library on Stellar (Soroban) lacks a validation mechanism for the fees quoted by Executors during the `send` flow. A malicious or compromised Executor can return an arbitrarily high fee for a cross-chain message, draining the entire balance of an OApp if the OApp has not configured a specific fee cap or if the default configuration is used.

## Vulnerability Detail
In [send_uln.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/message-libs/uln-302/src/send_uln.rs#L89-124):

```rust
let executor_fee = ILayerZeroExecutorClient::new(env, &executor).quote_executor(...);
let total_fee = native_fee + executor_fee;
// ... (passes total_fee back to EndpointV2 for payment)
```

The `ULN302` protocol trusts the `quote_executor` response blindly. An attacker participating as an Executor can monitor the `send` calls and return a quote of `type(i128).max`. Since the `EndpointV2` then attempts to transfer this amount from the OApp's approved balance, a successful transaction would result in a massive loss of funds for the OApp.

## Impact
High. Direct financial loss for OApps. Systematic drainage of protocol liquidity by malicious workers.

## Proof of Concept
1. OApp `X` attempts to send a message via `ULN302`.
2. Malicious Executor `M` is configured in the OApp's library settings.
3. `ULN302` calls `M.quote_executor(...)`.
4. `M` returns a fee of `1,000,000 XLM` (or any value exceeding the message value).
5. `ULN302` returns this fee to `EndpointV2`.
6. `EndpointV2` transfers `1,000,000 XLM` from OApp `X`.
7. **Result:** Loss of 1,000,000 XLM for the OApp.

## Recommended Mitigation
Implement a `MaxFee` configuration parameter in the OApp's `ULN302` settings. If the quoted fee exceeds the `MaxFee`, the transaction should revert. Additionally, integrate a protocol-wide "Sanity Cap" for message fees.

---
*"The swarm verifies, the hardware remembers."*
