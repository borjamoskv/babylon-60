# [M-04] Grace Period Limitation in Library Transitions in `MessageLibManager.rs`

## Summary
In the `set_receive_library` function of `MessageLibManager.rs`, a grace period can only be set when both the old and new libraries are custom (non-default). This limitation prevents OApps from having a safety window when transitioning from the global default library to their own custom library (or vice versa), forcing an instantaneous switch that can lead to dropped messages if the source chain has not yet synchronized its configuration.

## Vulnerability Detail
In [message_lib_manager.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/message_lib_manager.rs#L131-143):

```rust
let timeout = if grace_period > 0 {
    // To simplify timeout logic, we only allow setting timeout when both old and new libraries are custom (non-default).
    // ...
    assert_with_error!(env, old_lib.is_some() && new_lib.is_some(), EndpointError::OnlyNonDefaultLib);
    Some(Timeout { lib: old_lib.unwrap(), expiry: env.ledger().timestamp() + grace_period })
} else {
    None
};
```

This restriction is explicitly stated as being for "simplicity." However, in a real-world scenario, an OApp transitioning from the `DefaultReceiveLibrary` to its own `ReceiveLibrary` needs a grace period to capture any messages that were already in flight using the previous (default) library configuration. Without this, the message would be rejected by the endpoint if the delivery transaction reaches the destination chain after the configuration update but was signed on the source chain using the old library's parameters.

## Impact
Medium. Operational risk and message loss. Forced instantaneous transitions can lead to failed delivery of in-flight cross-chain messages.

## Proof of Concept
1. OApp `X` is using the `DefaultReceiveLibrary`.
2. A message is sent from the source chain and a signature from the Default DVN is pending.
3. OApp `X` calls `set_receive_library` to switch to their specialized `CustomReceiveLibrary` with `grace_period = 3600`.
4. **Result:** The transaction reverts with `OnlyNonDefaultLib`.
5. OApp `X` is forced to call `set_receive_library` with `grace_period = 0`.
6. The aforementioned pending message arrives at the destination.
7. **Result:** The `Endpoint` rejects the message because it was signed by the Default DVN, but the current library is now strictly the `CustomReceiveLibrary`.

## Recommended Mitigation
Remove the restriction on default libraries for grace periods. Implement logic to handle the transition from the `DefaultReceiveLibrary` to a custom one by allowing the `Timeout` to store the historical default library address.

---
*"The swarm verifies, the hardware remembers."*
