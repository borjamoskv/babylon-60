// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {CortexOracle} from "../src/CortexOracle.sol";

contract CortexOracleTest is Test {
    CortexOracle public oracle;
    address public dummyRouter = address(1);
    bytes32 public dummyDonId = bytes32("fun-ethereum-mainnet-1");

    function setUp() public {
        oracle = new CortexOracle(dummyRouter, dummyDonId);
    }

    function test_RequestTelemetryVerification() public {
        bytes32 mockHash = keccak256("c5-real-telemetry");
        string memory source = "return Functions.encodeString('verified');";
        
        // Ensure it emits
        vm.expectEmit(false, true, false, true);
        // The first argument is random so we skip check, second is the hash
        emit CortexOracle.TelemetryVerificationRequested(bytes32(0), mockHash);
        
        bytes32 reqId = oracle.requestTelemetryVerification(source, mockHash, 1, 300000);
        
        assertEq(oracle.lastTelemetryHash(), mockHash);
        assertTrue(reqId != bytes32(0));
    }

    function test_FulfillRequestSuccess() public {
        bytes32 reqId = keccak256("req1");
        
        oracle.fulfillRequest(reqId, bytes("verified"), new bytes(0));
        
        assertTrue(oracle.lastVerificationResult());
    }
}
