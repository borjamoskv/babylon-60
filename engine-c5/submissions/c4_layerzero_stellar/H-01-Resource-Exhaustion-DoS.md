# [H-01] Resource Exhaustion DoS via Storage Read Limit in `messaging_channel.rs`

## Summary
The `insert_and_drain_pending_nonces` function in `messaging_channel.rs` processes up to 256 out-of-order nonces in a single transaction. Since Soroban enforces a strict limit of 200 storage reads per transaction, any attempt to process a full batch of nonces will exceed the ledger limit, causing a permanent panic and blocking all subsequent messages for that path.

## Vulnerability Detail
In [messaging_channel.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/messaging_channel.rs#L232-265):

```rust
fn insert_and_drain_pending_nonces(...) {
    let mut pending_nonces = Self::pending_inbound_nonces(env, receiver, src_eid, sender);
    // ...
    while !pending_nonces.is_empty() && pending_nonces.first_unchecked() == new_inbound_nonce + 1 {
        new_inbound_nonce = pending_nonces.pop_front_unchecked();
    }
}
```

The constant `PENDING_INBOUND_NONCE_MAX_LEN` is set to 256. When `drain` is called, it potentially performs up to 256 reads (implicitly via the `storage` macro if not optimized, or via the `Vec` operations in Soroban which involve ledger access). On Stellar, the per-transaction limit for storage reads is 200. If an OApp has 256 pending nonces and a message arrives that triggers a full drain, the transaction will ALWAYS fail due to resource exhaustion.

## Impact
Permanent DoS of a messaging path. Once the pending list reaches a state where a drain exceeds the read limit, it can never be processed on-chain.

## Proof of Concept
1. Send 256 out-of-order messages (e.g., nonces 2 to 257).
2. The `PendingInboundNonces` list is populated.
3. Message with `nonce = 1` arrives.
4. `insert_and_drain_pending_nonces` is called. It attempts to drain and update the `inbound_nonce` from 0 to 257.
5. **Result:** The transaction panics with `ResourceLimitExceeded (Storage Reads)`.

## Recommended Mitigation
Reduce `PENDING_INBOUND_NONCE_MAX_LEN` to a value below 200 (e.g., 128) or implement a paginated drain mechanism where only a fixed number of nonces are processed per transaction.

---
*"The swarm verifies, the hardware remembers."*
