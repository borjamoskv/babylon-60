# [H-03] Event Phishing via Unauthorized `lz_compose_alert` in `messaging_composer.rs`

## Summary
The `lz_compose_alert` function in the `MessagingComposer` module lacks access control verification. While the function requires the caller to authenticate, it does not verify that the authenticated caller is an authorized Executor or a trusted component of the LayerZero protocol. This allows any address to emit legitimate-looking failure events for any OApp, creating a vector for large-scale phishing and social engineering attacks.

## Vulnerability Detail
In [messaging_composer.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/endpoint-v2/src/messaging_composer.rs#L62-91):

```rust
fn lz_compose_alert(
    env: &Env,
    executor: &Address,
    from: &Address,
    to: &Address,
    guid: &BytesN<32>,
    // ...
) {
    executor.require_auth(); // Only validates that the caller IS 'executor'
    // ... No check if 'executor' is authorized by the protocol ...
    LzComposeAlert {
        executor: executor.clone(),
        // ... (emits event)
    }
    .publish(env);
}
```

An attacker can call this function for any destination OApp (`to`), providing a malicious `message` and `reason` (e.g., "Critical: Funds at risk. Update here: [malicious_url]"). Since monitoring tools and OApp frontends listen to these events to inform users of cross-chain message status, the attacker can inject fraudulent alerts that appear to come from the official LayerZero Endpoint.

## Impact
High. Systemic trust risk. The vulnerability enables attackers to perform targeted phishing against high-value OApp users using the protocol's own event-emission infrastructure.

## Proof of Concept
1. Attacker address `A` calls `lz_compose_alert` with `to = Victim_OApp_Address`.
2. The transaction succeeds as long as `A` signs it.
3. The `LzComposeAlert` event is published to the ledger.
4. Block explorers and OApp dashboards display a "Failure Alert" for the OApp, including the attacker's malicious data.

## Recommended Mitigation
Implement an authorized executor registry. The `lz_compose_alert` function should verify that the `executor` address is either the officially configured executor for the OApp or is part of a global whitelist of trusted executors maintained by the Endpoint admin.

---
*"The swarm verifies, the hardware remembers."*
