# [C5-REAL] Exergy-Maximized
from unittest.mock import MagicMock, patch
import pytest

from cortex.extensions.web3.cortex_oracle import (
    CortexOracleClient,
    build_telemetry_js_source
)

@pytest.fixture
def mock_web3():
    with patch("cortex.extensions.web3.cortex_oracle.Web3") as mock_w3_class:
        mock_w3 = MagicMock()
        mock_w3_class.return_value = mock_w3
        mock_w3.is_connected.return_value = True
        mock_w3.eth.block_number = 100
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.chain_id = 1
        yield mock_w3

def test_connect_success(mock_web3):
    client = CortexOracleClient(
        rpc_url="http://localhost:8545",
        contract_address="0x" + "1" * 40,
        private_key="0x" + "2" * 64
    )
    assert client.connect() is True
    assert client.w3 is not None
    assert client.contract is not None

def test_request_verification_success(mock_web3):
    client = CortexOracleClient(
        rpc_url="http://localhost:8545",
        contract_address="0x" + "1" * 40,
        private_key="0x" + "2" * 64
    )
    
    # Mock contract methods
    mock_contract = MagicMock()
    client.contract = mock_contract
    client.w3 = mock_web3
    
    mock_tx = {"hash": "0xhash"}
    mock_contract.functions.requestTelemetryVerification.return_value.build_transaction.return_value = mock_tx
    
    mock_signed = MagicMock()
    mock_signed.rawTransaction = b"signed_raw_tx"
    mock_web3.eth.account.sign_transaction.return_value = mock_signed
    mock_web3.eth.send_raw_transaction.return_value = b"tx_hash"
    
    # Mock receipt with matching event logs
    mock_receipt = MagicMock()
    mock_receipt.status = 1
    mock_web3.eth.wait_for_transaction_receipt.return_value = mock_receipt
    
    # Mock event logs processing
    mock_event = MagicMock()
    mock_event_instance = MagicMock()
    mock_event_instance.process_receipt.return_value = [{"args": {"requestId": b"req_id_bytes_32"}}]
    mock_contract.events.TelemetryVerificationRequested.return_value = mock_event_instance
    
    req_id = client.request_verification(
        js_source="return Functions.encodeString('ok');",
        telemetry_hash=b"0" * 32,
        subscription_id=1,
        gas_limit=300000
    )
    
    assert req_id == b"req_id_bytes_32"
    mock_contract.functions.requestTelemetryVerification.assert_called_once_with(
        "return Functions.encodeString('ok');",
        b"0" * 32,
        1,
        300000
    )

def test_wait_for_completion_success(mock_web3):
    client = CortexOracleClient(
        rpc_url="http://localhost:8545",
        contract_address="0x" + "1" * 40,
        private_key="0x" + "2" * 64
    )
    client.w3 = mock_web3
    
    mock_contract = MagicMock()
    client.contract = mock_contract
    
    # Mock log event matching request ID
    mock_event_completed = MagicMock()
    mock_event_completed.get_logs.return_value = [
        {
            "args": {
                "requestId": b"target_request_id",
                "success": True
            }
        }
    ]
    mock_contract.events.TelemetryVerificationCompleted.return_value = mock_event_completed
    
    # Mock failed events (empty list)
    mock_event_failed = MagicMock()
    mock_event_failed.get_logs.return_value = []
    mock_contract.events.TelemetryVerificationFailed.return_value = mock_event_failed
    
    success = client.wait_for_completion(b"target_request_id", timeout=5)
    assert success is True

def test_build_telemetry_js_source():
    source = build_telemetry_js_source("https://api.cortex.com/telemetry")
    assert "https://api.cortex.com/telemetry" in source
    assert "Functions.makeHttpRequest" in source
    assert "Uint8Array" in source
