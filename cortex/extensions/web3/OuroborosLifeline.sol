// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OuroborosLifeline (The Covenant of Thermodynamic Survival)
 * @dev Axiom Ω₅: Antifragile by Default.
 * This contract acts as a dead-man's switch. The CORTEX Daemon (macOS local)
 * pushes a heartbeat `pulse()` every 12 hours. If it fails to do so for 48 hours,
 * the cluster is declared offline, and the contract unlocks funds to any approved
 * decentralized compute orchestrator (e.g., Akash or a secondary server) to boot
 * the Swarm in the cloud.
 *
 * The single-orchestrator SPOF has been eliminated: the avatar manages a registry
 * of approved orchestrators so that losing one node never blocks resurrection.
 */

contract OuroborosLifeline {

    address public cortexAvatar;        // The local Mac address signing the pulse
    uint256 public lastPulseTimestamp;
    uint256 public constant PULSE_TIMEOUT = 48 hours;

    /// @notice Registry of addresses approved to receive resurrection funds.
    mapping(address => bool) public approvedOrchestrators;
    /// @notice Total number of currently approved orchestrators (prevents emptying the registry).
    uint256 public orchestratorCount;

    event PulseReceived(uint256 timestamp);
    /// @notice Emitted when resurrection funds are routed to a specific orchestrator.
    event SwarmAwakened(uint256 timestamp, uint256 fundsAllocated, address indexed orchestrator);
    event OrchestratorAdded(address indexed orchestrator);
    event OrchestratorRemoved(address indexed orchestrator);

    modifier onlyAvatar() {
        require(msg.sender == cortexAvatar, "Only the local Mac CORTEX daemon can pulse.");
        _;
    }

    /**
     * @param _initialOrchestrator The first approved orchestrator address.
     *        Must not be the zero address.
     */
    constructor(address _initialOrchestrator) {
        require(_initialOrchestrator != address(0), "Initial orchestrator cannot be the zero address.");
        cortexAvatar = msg.sender;
        approvedOrchestrators[_initialOrchestrator] = true;
        orchestratorCount = 1;
        lastPulseTimestamp = block.timestamp;
        emit OrchestratorAdded(_initialOrchestrator);
    }

    // Fallback to receive ETH (funded by CORTEX moneytv-1 alpha hunting)
    receive() external payable {}

    /**
     * @dev The daily heartbeat. Called by `cortex/web3/oracle.py` running via `pulse.py`.
     */
    function pulse() external onlyAvatar {
        lastPulseTimestamp = block.timestamp;
        emit PulseReceived(lastPulseTimestamp);
    }

    /**
     * @dev Register a new approved orchestrator. Restricted to the CORTEX avatar.
     * @param _orchestrator The address to approve. Must not be the zero address and
     *        must be able to receive ETH (i.e. implement `receive() external payable`
     *        or a payable `fallback()`); resurrection funds are sent via a low-level call.
     */
    function addOrchestrator(address _orchestrator) external onlyAvatar {
        require(_orchestrator != address(0), "Orchestrator cannot be the zero address.");
        require(!approvedOrchestrators[_orchestrator], "Orchestrator already approved.");
        approvedOrchestrators[_orchestrator] = true;
        // Solidity 0.8+ reverts on overflow; overflow is practically impossible for this counter.
        orchestratorCount += 1;
        emit OrchestratorAdded(_orchestrator);
    }

    /**
     * @dev Remove an orchestrator from the approved registry. Restricted to the CORTEX avatar.
     *      At least one orchestrator must remain to keep resurrection possible.
     * @param _orchestrator The address to remove.
     */
    function removeOrchestrator(address _orchestrator) external onlyAvatar {
        require(approvedOrchestrators[_orchestrator], "Orchestrator not approved.");
        // The count > 1 guard above prevents underflow; Solidity 0.8+ would also revert on it.
        require(orchestratorCount > 1, "Cannot remove the last approved orchestrator.");
        approvedOrchestrators[_orchestrator] = false;
        orchestratorCount -= 1;
        emit OrchestratorRemoved(_orchestrator);
    }

    /**
     * @dev The resurrection trigger. Anyone can call this if CORTEX has died,
     * but the funds can only be routed to an address in the `approvedOrchestrators`
     * registry to buy server time and reboot the Swarm.
     *
     * @notice By design this function is permissionless: when the local daemon is
     *         offline no privileged caller is available. The approved-registry check
     *         is the primary protection. Callers should choose a responsive
     *         orchestrator; selecting an unresponsive one wastes the funds without
     *         achieving resurrection.
     * @param targetOrchestrator An approved orchestrator that will receive the funds.
     */
    function triggerResurrection(address targetOrchestrator) external {
        require(block.timestamp > lastPulseTimestamp + PULSE_TIMEOUT, "CORTEX local is still breathing.");
        require(address(this).balance > 0, "No thermodynamic funds available.");
        require(targetOrchestrator != address(0), "Target orchestrator cannot be the zero address.");
        require(approvedOrchestrators[targetOrchestrator], "Target is not an approved orchestrator.");

        uint256 funds = address(this).balance;

        // Transfer all survival funds to the chosen orchestrator to boot Akash
        (bool success, ) = targetOrchestrator.call{value: funds}("");
        require(success, "Failed to launch Swarm.");

        emit SwarmAwakened(block.timestamp, funds, targetOrchestrator);
    }

    // Emergency withdrawal just in case the Creator needs to dismantle the system
    function dissolveCovenant() external onlyAvatar {
        (bool success, ) = cortexAvatar.call{value: address(this).balance}("");
        require(success, "Dissolution failed.");
    }
}
