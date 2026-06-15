// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ICortexMemoryVerifier} from "./interfaces/ICortexMemoryVerifier.sol";
import {FunctionsClient} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/FunctionsClient.sol";
import {FunctionsRequest} from "@chainlink/contracts/src/v0.8/functions/v1_0_0/libraries/FunctionsRequest.sol";
import {CortexLineageRegistry} from "./CortexLineageRegistry.sol";

// C5-REAL telemetry Oracle using Chainlink Functions paradigm
contract CortexOracle is ICortexMemoryVerifier, FunctionsClient {
    using FunctionsRequest for FunctionsRequest.Request;

    bytes32 public immutable DON_ID;
    bytes32 public lastTelemetryHash;
    bool public lastVerificationResult;
    
    address public owner;
    address public registry;

    event TelemetryVerificationRequested(bytes32 indexed requestId, bytes32 indexed telemetryHash);
    event TelemetryVerificationCompleted(bytes32 indexed requestId, bool success);
    event TelemetryVerificationFailed(bytes32 indexed requestId, bytes error);
    event RegistryUpdated(address indexed oldRegistry, address indexed newRegistry);

    modifier onlyOwner() {
        _onlyOwner();
        _;
    }

    function _onlyOwner() internal view {
        require(msg.sender == owner, "CortexOracle: Only owner");
    }

    constructor(address _functionsRouter, bytes32 _donId, address _registry) FunctionsClient(_functionsRouter) {
        DON_ID = _donId;
        owner = msg.sender;
        registry = _registry;
    }

    function setRegistry(address _registry) external onlyOwner {
        emit RegistryUpdated(registry, _registry);
        registry = _registry;
    }

    // Function to trigger off-chain C5-REAL telemetry verification
    function requestTelemetryVerification(
        address agent,
        string calldata source,
        bytes32 telemetryHash,
        uint64 subscriptionId,
        uint32 gasLimit
    ) external returns (bytes32 requestId) {
        bytes memory pubKey = "";
        if (registry != address(0)) {
            pubKey = CortexLineageRegistry(registry).getAgentPublicKey(agent);
            CortexLineageRegistry(registry).registerRequest(telemetryHash);
        }

        FunctionsRequest.Request memory req;
        req.initializeRequestForInlineJavaScript(source);
        
        string[] memory args = new string[](2);
        args[0] = bytes32ToHexString(telemetryHash); 
        args[1] = bytesToHexString(pubKey);
        req.setArgs(args);

        requestId = _sendRequest(
            req.encodeCBOR(),
            subscriptionId,
            gasLimit,
            DON_ID
        );

        lastTelemetryHash = telemetryHash;
        emit TelemetryVerificationRequested(requestId, telemetryHash);
        
        return requestId;
    }

    // Callback that Chainlink DON calls
    function fulfillRequest(
        bytes32 requestId,
        bytes memory response,
        bytes memory err
    ) internal override {
        bool success = false;
        if (err.length == 0) {
            if (response.length > 0 && response[0] == 0x01) {
                success = true;
            }
            lastVerificationResult = success;
            emit TelemetryVerificationCompleted(requestId, success);
        } else {
            lastVerificationResult = false;
            emit TelemetryVerificationFailed(requestId, err);
        }

        // Registrar el resultado en el Ledger inmutable on-chain
        if (registry != address(0)) {
            CortexLineageRegistry(registry).registerRecord(lastTelemetryHash, success);
        }
    }

    function verifyTelemetry(bytes32 telemetryHash, bytes calldata proof) external view returns (bool) {
        if (registry != address(0)) {
            return CortexLineageRegistry(registry).isVerified(telemetryHash);
        }
        return telemetryHash == keccak256(proof);
    }

    function verifyLineage(bytes32 rootHash, bytes calldata proof) external view returns (bool) {
        if (registry != address(0)) {
            return CortexLineageRegistry(registry).isVerified(rootHash);
        }
        return rootHash == keccak256(proof);
    }

    // Helper functions for hex conversion
    function bytes32ToHexString(bytes32 value) public pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(64);
        for (uint256 i = 0; i < 32; i++) {
            str[i*2] = alphabet[uint8(value[i] >> 4)];
            str[i*2 + 1] = alphabet[uint8(value[i] & 0x0f)];
        }
        return string(str);
    }

    function bytesToHexString(bytes memory data) public pure returns (string memory) {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(data.length * 2);
        for (uint256 i = 0; i < data.length; i++) {
            str[i*2] = alphabet[uint8(data[i] >> 4)];
            str[i*2 + 1] = alphabet[uint8(data[i] & 0x0f)];
        }
        return string(str);
    }
}

