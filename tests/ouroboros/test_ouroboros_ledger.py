"""
Tests for Ouroboros Financial Ledger in PostgresPrimaryEngine.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from cortex.engine.postgres_primary import PostgresPrimaryEngine

@pytest.mark.asyncio
async def test_log_financial_transaction_generates_correct_sql_and_returns_id():
    mock_backend = MagicMock()
    mock_backend.execute_insert_with_conn = AsyncMock(return_value=101)
    
    # Needs async context manager for connection
    mock_conn = MagicMock()
    mock_backend.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_backend.connection.return_value.__aexit__ = AsyncMock()

    engine = PostgresPrimaryEngine(backend=mock_backend)
    
    # Call the new ledger tracking method
    engine._log_transaction = AsyncMock(return_value=999) # mock inside transaction
    
    tx_id = await engine.log_financial_transaction(
        tenant_id="tenant-test",
        strike_vector="algora_bounty",
        expected_yield=1200.0,
        compute_cost=5.0,
        net_yield=0.0,
        status="deployed"
    )
    
    assert tx_id == 101
    
    # Verify the correct SQL and parameters were passed
    mock_backend.execute_insert_with_conn.assert_called_once()
    args, kwargs = mock_backend.execute_insert_with_conn.call_args
    sql_arg = args[1]
    params_arg = args[2]
    
    assert "INSERT INTO financial_ledger" in sql_arg
    assert "tenant_id" in sql_arg
    assert "expected_yield" in sql_arg
    
    # Check that parameters are sequentially mapped
    assert params_arg[0] == "tenant-test"
    assert params_arg[1] == "algora_bounty"
    assert params_arg[2] == 1200.0
    assert params_arg[3] == 5.0
    assert params_arg[4] == 0.0
    assert params_arg[5] == "deployed"
    # ts is index 6
    assert params_arg[7] == 999
