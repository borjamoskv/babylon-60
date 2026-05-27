// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// Import local simulation workaround para no depender de layout absoluto
contract TargetToCorrupt {
    uint256 public lockedValue;
    bool public hasExploded;

    constructor() {
        lockedValue = 1000;
        hasExploded = false;
    }

    function complexOperation(uint256 x, uint256 y, uint256 z) public {
        unchecked {
            if (x * y + z == 89283471) {
                if (x < 1000 && y > 50000) {
                    hasExploded = true;
                }
            }
        }
    }
}

contract ChaosTest is Test {
    TargetToCorrupt target;

    function setUp() public {
        target = new TargetToCorrupt();
    }

    // Invariante Soberana
    function testFuzz_ChaosExplosion(uint256 x, uint256 y, uint256 z) public {
        target.complexOperation(x, y, z);
        assertEq(target.hasExploded(), false, "Chaos Reached! Memory Corrupted.");
    }
}
