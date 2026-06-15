// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ICortexMemoryVerifier {
    function verifyTelemetry(bytes32 telemetryHash, bytes calldata proof) external view returns (bool);
    function verifyLineage(bytes32 rootHash, bytes calldata proof) external view returns (bool);
}
