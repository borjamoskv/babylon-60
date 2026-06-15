// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {CortexOracle} from "../src/CortexOracle.sol";

contract DeployCortexOracle is Script {
    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address functionsRouter = vm.envAddress("FUNCTIONS_ROUTER");
        bytes32 donId = vm.envBytes32("DON_ID");

        vm.startBroadcast(deployerPrivateKey);

        CortexOracle oracle = new CortexOracle(functionsRouter, donId);
        console.log("CortexOracle deployed at:", address(oracle));

        vm.stopBroadcast();
    }
}
