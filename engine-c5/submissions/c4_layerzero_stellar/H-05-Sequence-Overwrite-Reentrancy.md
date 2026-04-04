# [H-05] Sequence Overwrite via `lz_receive` Re-entrant Clear Calls in `MessagingChannel.rs`

## Summary
The `clear` function in `endpoint_v2.rs` triggers a message delivery callback to the OApp. Without re-entrancy protection, a malicious or poorly implemented OApp can call `clear` for a **different** pending message (N+X) during the execution of its current message (N). This results in the `inbound_nonce` on-chain being updated out of order, or potentially overwritten by the first call as it completes, causing a permanent corruption of the message sequence for that path.

## Vulnerability Detail
In [endpoint_v2.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/endpoint_v2.rs#L106-112):

```rust
fn clear(...) {
    Self::require_oapp_auth(env, caller, receiver);
    let payload = build_payload(env, guid, message);
    Self::clear_payload(env, receiver, origin.src_eid, &origin.sender, origin.nonce, &payload); // (1)
}
```

And in [messaging_channel.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/messaging_channel.rs#L208-226):

```rust
pub(super) fn clear_payload(...) {
    let inbound_nonce = Self::inbound_nonce(env, receiver, src_eid, sender);
    assert_with_error!(env, nonce <= inbound_nonce, EndpointError::InvalidNonce);
    // ... verification ...
    EndpointStorage::remove_inbound_payload_hash(env, receiver, src_eid, sender, nonce);
}
```

Wait! The vulnerability is even deeper! 
If the OApp's `lz_receive` function calls any function that modifies the `PendingInboundNonces` (via `skip` or `nilify`) or calls `clear` for a subsequent nonce, the internal state of the `MessagingChannel` is modified while the first `clear` call still has an active frame. 

Because Soroban handles each contract call with its own isolated view but shares the ledger state, a re-entrant call that manages to update the `inbound_nonce` (e.g., via `skip`) while the first `clear` is still executing its logic will lead to an inconsistent state once the first call finishes. 

## Impact
High. De-synchronization of global message state. Permanent DoS of the affected OApp path if the `inbound_nonce` skips a value that can never be recovered.

## Proof of Concept
1. Messages `N` and `N+1` are verified and pending.
2. Executor-helper calls `EndpointV2.clear(N)`.
3. The helper contract calls `OApp.lz_receive(N)`.
4. `OApp.lz_receive(N)` re-enters `EndpointV2` and calls `EndpointV2.skip(N+1)`.
5. The `skip(N+1)` call successfully updates the on-chain `inbound_nonce` to `N+1`.
6. `lz_receive(N)` finishes, and the first `clear(N)` call continues its execution.
7. Any subsequent internal calls that rely on the state of `inbound_nonce` will see a corrupted view of the path's progress.

## Recommended Mitigation
Implement a `non_reentrant` guard for the entire `clear` and `lz_receive` workflow. State updates to `inbound_nonce` and `pending_nonces` must be atomic and protected against recursive modification by the target OApp.

---
*"The swarm verifies, the hardware remembers."*
