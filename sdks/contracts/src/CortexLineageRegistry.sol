// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CortexLineageRegistry
 * @dev Ledger de linajes y telemetría inmutable de agentes CORTEX en la EVM.
 */
contract CortexLineageRegistry {
    struct LineageRecord {
        bytes32 telemetryHash;
        uint256 timestamp;
        bool verified;
        address verifiedBy;
    }

    // Dirección del oráculo autorizado para certificar registros
    address public oracle;
    
    // Propietario del registro para administración básica
    address public owner;

    // Mapeo de hashes de telemetría a sus registros correspondientes
    mapping(bytes32 => LineageRecord) public records;

    // Mapeo de agentes a sus claves públicas (firmas criptográficas)
    mapping(address => bytes) public agentPublicKeys;

    // Mapeo de solicitudes de verificación a sus marcas de tiempo
    mapping(bytes32 => uint256) public requestTimestamps;

    event RecordRegistered(bytes32 indexed telemetryHash, bool indexed verified, address indexed verifiedBy);
    event OracleUpdated(address indexed oldOracle, address indexed newOracle);
    event AgentPublicKeyUpdated(address indexed agent, bytes publicKey);
    event RequestRegistered(bytes32 indexed telemetryHash, uint256 timestamp);
    event VerificationOverridden(bytes32 indexed telemetryHash, bool verified, address indexed overriddenBy);

    modifier onlyOwner() {
        require(msg.sender == owner, "CortexRegistry: Only owner");
        _;
    }

    modifier onlyAuthorized() {
        require(msg.sender == oracle || msg.sender == owner, "CortexRegistry: Not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setOracle(address _oracle) external onlyOwner {
        emit OracleUpdated(oracle, _oracle);
        oracle = _oracle;
    }

    /**
     * @dev Registra una clave pública para un agente.
     */
    function setAgentPublicKey(address agent, bytes calldata publicKey) external onlyOwner {
        agentPublicKeys[agent] = publicKey;
        emit AgentPublicKeyUpdated(agent, publicKey);
    }

    /**
     * @dev Obtiene la clave pública de un agente.
     */
    function getAgentPublicKey(address agent) external view returns (bytes memory) {
        return agentPublicKeys[agent];
    }

    /**
     * @dev Registra la marca de tiempo de una solicitud para habilitar el fallback de 24h.
     */
    function registerRequest(bytes32 telemetryHash) external onlyAuthorized {
        requestTimestamps[telemetryHash] = block.timestamp;
        emit RequestRegistered(telemetryHash, block.timestamp);
    }

    /**
     * @dev Registra un nuevo estado verificado en el Ledger on-chain.
     */
    function registerRecord(bytes32 telemetryHash, bool verified) external onlyAuthorized {
        records[telemetryHash] = LineageRecord({
            telemetryHash: telemetryHash,
            timestamp: block.timestamp,
            verified: verified,
            verifiedBy: msg.sender
        });

        emit RecordRegistered(telemetryHash, verified, msg.sender);
    }

    /**
     * @dev Permite al propietario anular manualmente la verificación tras un cooldown de 24 horas.
     */
    function overrideVerification(bytes32 telemetryHash, bool verified) external onlyOwner {
        require(requestTimestamps[telemetryHash] != 0, "Registry: Request not found");
        require(block.timestamp >= requestTimestamps[telemetryHash] + 24 hours, "Registry: Cooldown active");

        records[telemetryHash] = LineageRecord({
            telemetryHash: telemetryHash,
            timestamp: block.timestamp,
            verified: verified,
            verifiedBy: msg.sender
        });

        emit VerificationOverridden(telemetryHash, verified, msg.sender);
        emit RecordRegistered(telemetryHash, verified, msg.sender);
    }

    /**
     * @dev Verifica si un hash de telemetría específico ha sido certificado.
     */
    function isVerified(bytes32 telemetryHash) external view returns (bool) {
        return records[telemetryHash].verified;
    }
}
