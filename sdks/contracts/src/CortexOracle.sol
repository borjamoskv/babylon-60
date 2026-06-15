// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ICortexMemoryVerifier} from "./interfaces/ICortexMemoryVerifier.sol";

// Abstract interface for Chainlink Functions router to allow compilation 
// if the library structure changes slightly. In production, import directly from @chainlink/contracts.
interface IFunctionsRouter {
    function getAllowListId() external view returns (bytes32);
    function setAllowListId(bytes32 allowListId) external;
}

// Minimal implementation of C5-REAL telemetry Oracle using Chainlink Functions paradigm
contract CortexOracle is ICortexMemoryVerifier {
    address public immutable functionsRouter;
    bytes32 public immutable donId;

    bytes32 public lastTelemetryHash;
    bool public lastVerificationResult;

    event TelemetryVerificationRequested(bytes32 indexed requestId, bytes32 indexed telemetryHash);
    event TelemetryVerificationCompleted(bytes32 indexed requestId, bool success);

    constructor(address _functionsRouter, bytes32 _donId) {
        functionsRouter = _functionsRouter;
        donId = _donId;
    }

    // Function to trigger off-chain C5-REAL telemetry verification
    // Simulating the FunctionsClient behavior for the scaffold
    function requestTelemetryVerification(
        string calldata source,
        bytes32 telemetryHash,
        uint64 subscriptionId,
        uint32 gasLimit
    ) external returns (bytes32 requestId) {
        // Emit request event
        requestId = keccak256(abi.encodePacked(source, telemetryHash, block.timestamp));
        lastTelemetryHash = telemetryHash;

        emit TelemetryVerificationRequested(requestId, telemetryHash);
        return requestId;
    }

    // Callback that Chainlink DON calls
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) external {
        // Require caller is the router in a real impl
        // require(msg.sender == functionsRouter, "Only router can fulfill");

        if (err.length == 0) {
            lastVerificationResult = true;
            emit TelemetryVerificationCompleted(requestId, true);
        } else {
            lastVerificationResult = false;
            emit TelemetryVerificationCompleted(requestId, false);
        }
    }

    function verifyTelemetry(bytes32 telemetryHash, bytes calldata proof) external pure returns (bool) {
        // Fallback for direct proof injection
        return telemetryHash == keccak256(proof);
    }

    function verifyLineage(bytes32 rootHash, bytes calldata proof) external pure returns (bool) {
        // Fallback for lineage
        return rootHash == keccak256(proof);
    }
}
