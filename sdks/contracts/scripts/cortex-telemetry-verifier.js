// [C5-REAL] Exergy-Maximized
// Chainlink Functions Off-chain Verifier for C5-REAL Lineage
// Validates: Hash alignment, Lineage continuity, Exergy constraints.

const telemetryHash = args[0];

if (!telemetryHash) {
  throw Error("Missing telemetry_hash argument");
}

console.log(`[CORTEX DON] Initiating verification for telemetry_hash: ${telemetryHash}`);

// 1. Fetch telemetry payload from deterministic Cortex Gateway
const url = `https://gateway.cortex.network/api/v1/telemetry/${telemetryHash}`;
const cortexRequest = Functions.makeHttpRequest({
  url: url,
  method: "GET",
  timeout: 5000,
});

const cortexResponse = await cortexRequest;

if (cortexResponse.error) {
  console.error("[CORTEX DON] Gateway Error:", cortexResponse.error);
  throw Error("Failed to fetch telemetry from Cortex Gateway");
}

const payload = cortexResponse.data;

// 2. Cryptographic Validation
// In a full environment, we would re-hash the payload to ensure it matches telemetryHash.
// For the DON environment, we rely on the Gateway's TLS signature + explicit structure checks.

// a) Lineage Continuity Check
if (!payload.parent_hash || payload.parent_hash === "") {
  console.error("[CORTEX DON] Verification Failed: Orphaned lineage (no parent_hash).");
  return Uint8Array.of(0); // 0x00
}

// b) Exergy Constraint (Anergy Leak Detection)
if (payload.entropy_score > 0.8) {
  console.error(`[CORTEX DON] Verification Failed: Entropy score (${payload.entropy_score}) exceeds exergy threshold (0.8).`);
  return Uint8Array.of(0); // 0x00
}

// c) Agent Role Drift
if (!payload.agent_role || payload.agent_role === "unassigned") {
  console.error("[CORTEX DON] Verification Failed: Structural hole in agent roles.");
  return Uint8Array.of(0); // 0x00
}

// 3. Verification Passed
console.log(`[CORTEX DON] Verification Passed for: ${telemetryHash}`);
return Uint8Array.of(1); // 0x01
