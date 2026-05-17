// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

// Mock interface for MultiVault highlighting the vulnerability
contract VulnerableMultiVault {
    mapping(uint256 => int256) public totalUtilization;
    mapping(uint256 => bool) public hasRolledOverSystemUtilization;
    uint256 public currentEpoch;

    function setCurrentEpoch(uint256 _epoch) external {
        currentEpoch = _epoch;
    }

    function setTotalUtilization(uint256 _epoch, int256 _value) external {
        totalUtilization[_epoch] = _value;
    }

    // Vulnerable rollover logic as found in the audit
    function _rollover() public {
        uint256 currentEpochLocal = currentEpoch;
        if (currentEpochLocal > 0 && !hasRolledOverSystemUtilization[currentEpochLocal]) {
            hasRolledOverSystemUtilization[currentEpochLocal] = true;

            uint256 previousEpoch = currentEpochLocal - 1;
            int256 previousEpochUtilization = totalUtilization[previousEpoch];
            
            // BUG: It only looks at previousEpoch. If previousEpoch was skipped (utilization 0),
            // it fails to propagate the state from previousEpoch - 1.
            if (previousEpochUtilization != 0 && totalUtilization[currentEpochLocal] == 0) {
                totalUtilization[currentEpochLocal] = previousEpochUtilization;
            }
        }
    }

    function getTotalUtilization(uint256 epoch) external view returns (int256) {
        return totalUtilization[epoch];
    }
}

contract IntuitionRolloverTest is Test {
    VulnerableMultiVault public vault;

    function setUp() public {
        vault = new VulnerableMultiVault();
    }

    function test_SkippedEpochResetsUtilization() public {
        // 1. Initial State: Epoch 0 has 1000 utilization
        vault.setTotalUtilization(0, 1000);
        
        // 2. Epoch 1: Normal activity occurs, utilization propagates
        vault.setCurrentEpoch(1);
        vault._rollover();
        assertEq(vault.getTotalUtilization(1), 1000, "Epoch 1 should have rolled over from 0");

        // 3. Epoch 2: NO activity occurs. totalUtilization[2] remains 0.
        // vault._rollover() is NOT called in Epoch 2 because there are no transactions.
        vault.setCurrentEpoch(2); 
        // totalUtilization[2] is 0 (default)

        // 4. Epoch 3: Activity resumes. 
        vault.setCurrentEpoch(3);
        vault._rollover();

        // FAILURE: Since totalUtilization[2] is 0, the rollover logic in Epoch 3
        // sees previousEpochUtilization == 0 and does NOTHING.
        // The utilization of 1000 from Epoch 1 is LOST.
        
        int256 utilizationEpoch3 = vault.getTotalUtilization(3);
        console.log("Utilization in Epoch 3:", utilizationEpoch3);
        
        assertEq(utilizationEpoch3, 0, "VULNERABILITY CONFIRMED: System utilization reset to 0 due to skipped epoch");
    }
}
