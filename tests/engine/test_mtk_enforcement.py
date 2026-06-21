# [C5-REAL] Exergy-Maximized
"""
MTK Physical Enforcement Test.
Validates that the MTK acts as an absolute physical boundary against state mutation.
"""

import sqlite3
import pytest
import datetime
from cortex.engine.mtk_sqlite_authorizer import install_mtk_authorizer
from cortex.engine.mtk_core import MTKGuard
from cortex.types.evidence import ClosurePayload, EvidenceBundle

@pytest.fixture
def mtk_db():
    conn = sqlite3.connect(":memory:")
    # Initialize schema so authorizer doesn't block it (we ignore sqlite_ schemas in the hook)
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, data TEXT)")
    
    # Install the physical barrier
    install_mtk_authorizer(conn)
    return conn

@pytest.fixture
def dummy_payload():
    evidence = EvidenceBundle.forge(
        query="dummy",
        sources=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    )
    return ClosurePayload.seal(
        claims=[{"claim": "test"}],
        evidence=evidence,
        verdict=True
    )

def test_mtk_blocks_unauthorized_mutation(mtk_db):
    """
    Attempt to mutate state directly without an MTK token.
    This simulates a "Silent Bypass" attempt. The SQLite engine must physically reject it.
    """
    with pytest.raises(sqlite3.DatabaseError) as exc_info:
        mtk_db.execute("INSERT INTO records (data) VALUES ('unauthorized')")
        
    assert "not authorized" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_mtk_allows_authorized_mutation(mtk_db, dummy_payload):
    """
    Attempt to mutate state through the MTK physical boundary.
    The mutation must succeed.
    """
    guard = MTKGuard(private_key="test_key_123")
    
    async with guard.transaction_boundary(dummy_payload) as token:
        assert token.startswith("mtk_auth_")
        # Now authorized, this should not raise DatabaseError
        cursor = mtk_db.execute("INSERT INTO records (data) VALUES ('authorized')")
        assert cursor.rowcount == 1
        
    # Once outside the boundary, mutation should be blocked again
    with pytest.raises(sqlite3.DatabaseError):
        mtk_db.execute("INSERT INTO records (data) VALUES ('unauthorized_after')")

@pytest.mark.asyncio
async def test_mtk_rejects_invalid_payload():
    """
    MTK must reject negative verdicts immediately without minting a token.
    """
    guard = MTKGuard(private_key="test_key_123")
    evidence = EvidenceBundle.forge(
        query="dummy",
        sources=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    )
    payload_negative = ClosurePayload.seal(
        claims=[{"claim": "test"}],
        evidence=evidence,
        verdict=False  # Invalid causality
    )
    
    with pytest.raises(ValueError, match="MTK-REJECT"):
        async with guard.transaction_boundary(payload_negative):
            pass

