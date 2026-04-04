# [H-04] Fee Refund Hijacking via Re-entrant Token Callbacks in `EndpointV2.rs`

## Summary
The `pay_messaging_fees` function in `endpoint_v2.rs` iterates over fee recipients and transfers tokens before issuing a refund to the sender. If the native token or a ZRO token implements callbacks (common in SEP-41 extensions or malicious contract addresses), a re-entrant call can hijack the balance calculation. This allows a malicious OApp to overdraw refunds or "steal" the fees supplied by other OApps in the same transaction context.

## Vulnerability Detail
In [endpoint_v2.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/endpoint_v2.rs#L244-306):

```rust
fn pay_messaging_fees(...) {
    let mut native_fee_supplied = native_token_client.balance(&this_contract); // (1)
    
    native_fee_recipients.iter().for_each(|r| {
        native_token_client.transfer(&this_contract, &r.to, &r.amount); // (2)
    });
    
    if native_fee_supplied > 0 {
        native_token_client.transfer(&this_contract, refund_address, &native_fee_supplied); // (3)
    }
}
```

The function captures the contract's total balance (1) as the amount to be refunded after paying recipients. If the `transfer` (2) calls a recipient that triggers a re-entrant `EndpointV2.send(...)` call, the contract's balance is modified before the first call reaches the final refund step (3). 

In a multi-message batch, `native_fee_supplied` includes the fees for all messages. A malicious `refund_address` or recipient in the first message can use the re-entrant call to reduce the remaining balance, such that when the final message's refund is processed, the contract has insufficient funds or over-refunds from the wrong pool.

## Impact
High. Financial loss for OApps and the LayerZero protocol. Systematic drainage of fee balances in the Endpoint contract.

## Proof of Concept
1. Attacker OApp sends a message with a high fee.
2. `pay_messaging_fees` captures the total balance (including other OApp fees).
3. The transfer to a recipient triggers a re-entrant call to `EndpointV2.send(...)` for a different message.
4. The contract state is interleaved. The final refund (3) is calculated on the *initial* total balance, effectively "stealing" the funds supplied by other OApps that were still in the contract.

## Recommended Mitigation
Implement a `non_reentrant` guard for the `send` and `pay_messaging_fees` functions. Additionally, calculate the refund amount based on the `native_fee` actually quoted for the specific message, rather than querying the total balance of the contract.

---
*"The swarm verifies, the hardware remembers."*
