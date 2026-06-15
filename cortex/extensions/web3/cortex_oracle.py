# [C5-REAL] Exergy-Maximized
import json
import logging
import os
import time
from typing import Dict, Any, Optional

from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware

logger = logging.getLogger("cortex.web3.oracle")

RPC_URL = os.environ.get("CORTEX_RPC_URL", "https://mainnet.base.org")
CONTRACT_ADDRESS = os.environ.get("CORTEX_ORACLE_CONTRACT")
PRIVATE_KEY = os.environ.get("CORTEX_WALLET_KEY")
DEFAULT_SUB_ID = int(os.environ.get("CORTEX_FUNCTIONS_SUB_ID", "0"))
DEFAULT_GAS_LIMIT = int(os.environ.get("CORTEX_FUNCTIONS_GAS_LIMIT", "300000"))

CORTEX_ORACLE_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "source", "type": "string"},
            {"internalType": "bytes32", "name": "telemetryHash", "type": "bytes32"},
            {"internalType": "uint64", "name": "subscriptionId", "type": "uint64"},
            {"internalType": "uint32", "name": "gasLimit", "type": "uint32"}
        ],
        "name": "requestTelemetryVerification",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "lastVerificationResult",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "requestId", "type": "bytes32"},
            {"indexed": True, "internalType": "bytes32", "name": "telemetryHash", "type": "bytes32"}
        ],
        "name": "TelemetryVerificationRequested",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "requestId", "type": "bytes32"},
            {"indexed": False, "internalType": "bool", "name": "success", "type": "bool"}
        ],
        "name": "TelemetryVerificationCompleted",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "requestId", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes", "name": "error", "type": "bytes"}
        ],
        "name": "TelemetryVerificationFailed",
        "type": "event"
    }
]

class CortexOracleClient:
    def __init__(self, rpc_url: str = RPC_URL, contract_address: Optional[str] = CONTRACT_ADDRESS, private_key: Optional[str] = PRIVATE_KEY):
        self.rpc_url = rpc_url
        self.contract_address = contract_address
        self.private_key = private_key
        self.w3: Optional[Web3] = None
        self.contract: Optional[Any] = None

    def connect(self) -> bool:
        if self.w3 and self.contract:
            return True
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            if not self.w3.is_connected():
                logger.error(f"[CortexOracle] Connection failed to {self.rpc_url}")
                return False
            
            if self.contract_address:
                checksum_address = Web3.to_checksum_address(self.contract_address)
                self.contract = self.w3.eth.contract(address=checksum_address, abi=CORTEX_ORACLE_ABI)
            return True
        except Exception as e:
            logger.error(f"[CortexOracle] Connection setup error: {e}")
            return False

    def request_verification(
        self, 
        js_source: str, 
        telemetry_hash: bytes, 
        subscription_id: int = DEFAULT_SUB_ID, 
        gas_limit: int = DEFAULT_GAS_LIMIT
    ) -> Optional[bytes]:
        """
        Sends a transaction to request telemetry verification via Chainlink Functions.
        """
        if not self.connect() or not self.contract or not self.w3 or not self.private_key:
            logger.error("[CortexOracle] Missing connection credentials or contract address.")
            return None

        try:
            account = self.w3.eth.account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            # Format arguments for call
            # telemetry_hash must be a 32-byte hash
            if len(telemetry_hash) != 32:
                raise ValueError("Telemetry hash must be exactly 32 bytes.")

            tx = self.contract.functions.requestTelemetryVerification(
                js_source,
                telemetry_hash,
                subscription_id,
                gas_limit
            ).build_transaction({
                "chainId": self.w3.eth.chain_id,
                "gas": gas_limit + 100000, # Buffer for tx execution
                "gasPrice": self.w3.eth.gas_price,
                "nonce": nonce,
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            logger.info(f"[CortexOracle] Telemetry verification tx sent. Hash: {self.w3.to_hex(tx_hash)}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1: # type: ignore
                logger.error("[CortexOracle] Transaction failed.")
                return None

            # Extract requestId from logs
            logs = self.contract.events.TelemetryVerificationRequested().process_receipt(receipt)
            if logs:
                request_id = logs[0]["args"]["requestId"]
                logger.info(f"[CortexOracle] Verification request registered. Request ID: {self.w3.to_hex(request_id)}")
                return request_id
            
            logger.warning("[CortexOracle] Transaction succeeded but TelemetryVerificationRequested event not found.")
            return None
        except Exception as e:
            logger.error(f"[CortexOracle] Verification request failed: {e}")
            return None

    def wait_for_completion(self, request_id: bytes, timeout: int = 180) -> Optional[bool]:
        """
        Polls the chain for verification completion logs matching the request ID.
        """
        if not self.connect() or not self.contract or not self.w3:
            return None

        start_time = time.time()
        logger.info(f"[CortexOracle] Polling for fulfillment of request: {self.w3.to_hex(request_id)}")

        # Keep track of latest block checked to optimize filter ranges
        latest_block = self.w3.eth.block_number

        while time.time() - start_time < timeout:
            try:
                # Query logs from contract events
                completed_events = self.contract.events.TelemetryVerificationCompleted().get_logs(
                    fromBlock=latest_block - 10,
                    toBlock='latest'
                )
                for event in completed_events:
                    if event["args"]["requestId"] == request_id:
                        success = event["args"]["success"]
                        logger.info(f"[CortexOracle] Request {self.w3.to_hex(request_id)} completed. Success: {success}")
                        return success

                failed_events = self.contract.events.TelemetryVerificationFailed().get_logs(
                    fromBlock=latest_block - 10,
                    toBlock='latest'
                )
                for event in failed_events:
                    if event["args"]["requestId"] == request_id:
                        err_reason = event["args"]["error"]
                        logger.error(f"[CortexOracle] Request {self.w3.to_hex(request_id)} failed with error: {err_reason.hex()}")
                        return False

                time.sleep(5)
            except Exception as e:
                logger.warning(f"[CortexOracle] Error while polling events: {e}")
                time.sleep(5)

        logger.error(f"[CortexOracle] Timeout reached waiting for request {self.w3.to_hex(request_id)} completion.")
        return None

def build_telemetry_js_source(api_endpoint: str) -> str:
    """
    Builds the Chainlink Functions source script that queries the telemetry API.
    """
    return f"""
    const telemetryHash = args[0];
    const url = "{api_endpoint}/" + telemetryHash;
    const response = await Functions.makeHttpRequest({{ url: url }});
    if (response.error) {{
        throw Error("API Request failed");
    }}
    const data = response.data;
    if (data && data.verified === true) {{
        return new Uint8Array([1]);
    }}
    return new Uint8Array([0]);
    """
