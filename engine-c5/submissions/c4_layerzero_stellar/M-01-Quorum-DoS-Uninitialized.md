# [M-01] Quorum DoS via Uninitialized DVN Accounts in `ULN302`

## Summary
The `ULN302` library on Stellar (Soroban) calculates a quorum from a list of DVNs (Decentralized Verifier Networks). However, it does not explicitly handle uninitialized accounts on Stellar. If a configured DVN account has not been funded/initialized on Stellar, any transaction attempting to verify its signature will panic, leading to a temporary DoS for the OApp's messaging path until the configuration is updated or the account is initialized.

## Vulnerability Detail
In [send_uln.rs](file:///Users/borjafernandezangulo/Cortex-Persist/engine-c5/targets/2026-04-layerzero/contracts/protocol/stellar/contracts/message-libs/uln-302/src/send_uln.rs#L89-124):

The library iterates over the configured DVNs to collect quotes and signatures. In Stellar, unlike Ethereum, a raw address must be "initialized" in the ledger with a minimum balance before it can be interacted with via some token or account operations. If a DVN is added to the configuration but its account is not initialized on the Stellar network, the call to `verify` or `quote` for that DVN in the `EndpointV2` or `ULN302` context will panic.

## Impact
Medium. Temporary DoS of the affected OApp path. The path remains blocked until the DVN is initialized or the OApp changes its configuration.

## Proof of Concept
1. OApp configures a quorum of 2 DVNs: `DVN_A` (initialized) and `DVN_B` (uninitialized).
2. OApp attempts to send a message.
3. `ULN302` calls `quote` for `DVN_B`.
4. **Result:** The transaction panics because `DVN_B` does not exist as a funded account in the Stellar ledger.

## Recommended Mitigation
Implement a existence check (e.g., `env.accounts().exists(&dvn_address)`) before calling into a DVN and handle uninitialized accounts gracefully or revert with a descriptive error. Alternatively, ensure the DVN registration flow requires proof of initialization.

---
*"The swarm verifies, the hardware remembers."*
